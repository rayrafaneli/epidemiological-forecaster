"""
src/extract/ibge_extractor.py
===============================================================================
CAMADA: extract

O QUE ESTE ARQUIVO FAZ
-----------------------
Busca no IBGE três informações que, juntas, formam a tabela `municipios`:

1) get_municipios(uf)     -> lista de municípios de uma UF (API de Localidades)
2) get_populacao()        -> estimativa populacional mais recente por município (API SIDRA)
3) get_area_territorial() -> área em km² por município (API SIDRA)

POR QUE DUAS APIs DIFERENTES DO IBGE?
-----------------------
A API de "Localidades" (servicodados.ibge.gov.br) é ótima para nomes,
hierarquia (UF/região) e códigos, mas não traz indicadores estatísticos.
Já a API "SIDRA" (apisidra.ibge.gov.br) é o acervo de tabelas estatísticas
do IBGE (Censo, estimativas populacionais, área territorial etc). Por isso
combinamos as duas e o Transform depois junta (`merge`) tudo pelo código do
município (`codigo_ibge`), que é a chave comum entre elas.
===============================================================================
"""

import pandas as pd

from src.extract.base_extractor import BaseExtractor
from src.config import config
from src.logger import get_logger

logger = get_logger(__name__)

# Códigos SIDRA usados:
# Agregado 6579 = "População residente estimada"; variável 9324 = população (pessoas)
SIDRA_AGREGADO_POPULACAO = 6579
SIDRA_VARIAVEL_POPULACAO = 9324

# Agregado 1301 = "Área territorial"; variável 615 = área da unidade territorial (km²)
SIDRA_AGREGADO_AREA = 1301
SIDRA_VARIAVEL_AREA = 615


class IbgeExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.localidades_base_url = config.ibge.localidades_base_url
        self.sidra_base_url = config.ibge.sidra_base_url

    def get_municipios(self, uf: str | None = None) -> pd.DataFrame:
        """
        Retorna os municípios de uma UF com código IBGE, nome, UF e região.
        Endpoint: /localidades/estados/{uf}/municipios
        """
        uf = uf or config.ibge.uf
        url = f"{self.localidades_base_url}/estados/{uf}/municipios"
        logger.info(f"Buscando municípios do IBGE para UF={uf}...")
        raw = self._get(url)

        if not raw:
            logger.warning(f"Nenhum município retornado para UF={uf}.")
            return pd.DataFrame()

        # A resposta é uma lista de objetos aninhados, por exemplo:
        # { "id": 2611606, "nome": "Recife",
        #   "microrregiao": {"mesorregiao": {"UF": {"sigla": "PE", "nome": "Pernambuco",
        #       "regiao": {"nome": "Nordeste"}}}}}
        # Por isso "achatamos" (flatten) manualmente os campos que interessam.
        registros = []
        for item in raw:
            uf_info = item.get("microrregiao", {}).get("mesorregiao", {}).get("UF", {})
            registros.append({
                "codigo_ibge": item.get("id"),
                "nome": item.get("nome"),
                "uf": uf_info.get("sigla"),
                "regiao": uf_info.get("regiao", {}).get("nome"),
            })

        df = pd.DataFrame(registros)
        logger.info(f"{len(df)} municípios encontrados para UF={uf}.")
        return df

    def _fetch_sidra_indicator(
        self, agregado: int, variavel: int, codigos_municipio: list[int]
    ) -> pd.DataFrame:
        """
        Função genérica para buscar um indicador do SIDRA para uma lista de
        municípios específica.

        Formato da URL do SIDRA:
            /t/{agregado}/n6/{codigo1,codigo2,...}/v/{variavel}/p/last

        - "t" = tabela/agregado
        - "n6" = nível geográfico "município", seguido dos códigos desejados
        - "v"  = variável
        - "p/last" = período mais recente disponível

        A resposta do SIDRA vem como uma lista onde o PRIMEIRO item é um
        "cabeçalho" (nomes descritivos das colunas) e os demais são os
        dados de fato. Por isso descartamos raw[0] com raw[1:].
        """
        codigos_str = ",".join(str(c) for c in codigos_municipio)
        url = f"{self.sidra_base_url}/t/{agregado}/n6/{codigos_str}/v/{variavel}/p/last"

        raw = self._get(url)
        if not raw or len(raw) < 2:
            logger.warning(f"SIDRA não retornou dados para agregado={agregado}, variavel={variavel}.")
            return pd.DataFrame()

        dados = raw[1:]  # remove o cabeçalho descritivo
        registros = []
        for item in dados:
            # ATENÇÃO: na estrutura de resposta do SIDRA para este agregado,
            # "D2N" é o NOME DA VARIÁVEL (ex: "População residente estimada"),
            # não o período. O ano de referência vem em "D3N" (ex: "2024").
            # Isso só foi possível confirmar rodando contra a API real -
            # documentado aqui para quem for mexer de novo no futuro.
            periodo_raw = item.get("D3N")
            registros.append({
                "codigo_ibge": int(item.get("D1C")),   # código do município
                "valor": item.get("V"),                 # valor do indicador
                "periodo": periodo_raw,                  # ano/período de referência (ex: "2024")
            })
        return pd.DataFrame(registros)

    def get_populacao(self, codigos_municipio: list[int]) -> pd.DataFrame:
        """Estimativa populacional mais recente, por município."""
        logger.info(f"Buscando população estimada no SIDRA para {len(codigos_municipio)} município(s)...")
        df = self._fetch_sidra_indicator(
            SIDRA_AGREGADO_POPULACAO, SIDRA_VARIAVEL_POPULACAO, codigos_municipio
        )
        return df.rename(columns={"valor": "populacao_estimada", "periodo": "ano_referencia_populacao"})

    def get_area_territorial(self, codigos_municipio: list[int]) -> pd.DataFrame:
        """Área territorial (km²) de cada município."""
        logger.info(f"Buscando área territorial no SIDRA para {len(codigos_municipio)} município(s)...")
        df = self._fetch_sidra_indicator(
            SIDRA_AGREGADO_AREA, SIDRA_VARIAVEL_AREA, codigos_municipio
        )
        return df.rename(columns={"valor": "area_km2"}).drop(columns=["periodo"], errors="ignore")


if __name__ == "__main__":
    # Uso: python -m src.extract.ibge_extractor
    extractor = IbgeExtractor()
    municipios_df = extractor.get_municipios()
    print(municipios_df.head())

    if not municipios_df.empty:
        codigos = municipios_df["codigo_ibge"].tolist()
        pop_df = extractor.get_populacao(codigos)
        area_df = extractor.get_area_territorial(codigos)
        print(pop_df.head())
        print(area_df.head())
