"""Catálogo baseline NBR-000: autoridade localizada, estado indexed."""

from __future__ import annotations

from nbr12721.normative.locator import PageLocator, PrintedPage
from nbr12721.normative.reference import NormativeReference
from nbr12721.normative.source import NormativeSource, baseline_normative_source
from nbr12721.normative.vocab import SOURCE_ID


def _arabic(pdf_page: int, label: str) -> PageLocator:
    return PageLocator(
        pdf_page=pdf_page,
        printed_page=PrintedPage(kind="arabic", label=label),
    )


def _roman(pdf_page: int, label: str) -> PageLocator:
    return PageLocator(
        pdf_page=pdf_page,
        printed_page=PrintedPage(kind="roman", label=label),
    )


def _absent(pdf_page: int, reason: str) -> PageLocator:
    return PageLocator(
        pdf_page=pdf_page,
        printed_page=PrintedPage(kind="absent", reason=reason),
    )


def _ref(
    *,
    suffix: str,
    section: str,
    locator: PageLocator,
    reference_type: str,
    description: str,
    edition_notes: str = "",
    cross_references: tuple[str, ...] = (),
    authority_refs: tuple[str, ...] = (),
) -> NormativeReference:
    return NormativeReference(
        id=f"nbr12721:2006:vc3:{suffix}",
        source_id=SOURCE_ID,
        section=section,
        locator=locator,
        reference_type=reference_type,
        formalization_state="indexed",
        description=description,
        edition_notes=edition_notes,
        cross_references=cross_references,
        authority_refs=authority_refs,
    )


def baseline_references() -> tuple[NormativeReference, ...]:
    """Cobertura inicial obrigatória (paráfrases curtas; sem transcrição)."""
    cover = _ref(
        suffix="cover-identity",
        section="Capa / identificação da edição",
        locator=_absent(
            1,
            "capa do PDF sem foliação impressa; identificação de edição na frente",
        ),
        reference_type="definition_classification",
        description=(
            "Identifica ABNT NBR 12721:2006, segunda edição e versão "
            "corrigida 3; metadado 2021 não cria edição 2021."
        ),
        edition_notes=(
            "Publicação 2006-08-28; versão corrigida 3 em 2021-01-19."
        ),
        cross_references=("nbr12721:2006:vc3:preface",),
    )
    preface = _ref(
        suffix="preface",
        section="Prefácio",
        locator=_roman(6, "vi"),
        reference_type="definition_classification",
        description=(
            "Registra incorporação das Erratas 1 e 2 (2007) e da Errata 3 "
            "(2021-01-19) na versão corrigida 3."
        ),
        edition_notes="Autoridade editorial da vc3; sem mudança de ano da norma.",
        authority_refs=("nbr12721:2006:vc3:cover-identity",),
    )
    sec_37 = _ref(
        suffix="sec-3.7",
        section="3.7",
        locator=_arabic(10, "2"),
        reference_type="definition_classification",
        description=(
            "Classifica áreas por dimensões ortogonais de uso, padrão de "
            "custo e forma de divisão (além da área real)."
        ),
    )
    sec_3721 = _ref(
        suffix="sec-3.7.2.1",
        section="3.7.2.1",
        locator=_arabic(11, "3"),
        reference_type="definition_classification",
        description=(
            "Separa área privativa principal e área privativa acessória."
        ),
        cross_references=("nbr12721:2006:vc3:sec-3.7",),
    )
    sec_3722 = _ref(
        suffix="sec-3.7.2.2",
        section="3.7.2.2",
        locator=_arabic(11, "3"),
        reference_type="definition_classification",
        description=(
            "Introduz a classificação normativa das áreas de vaga de "
            "garagem, detalhada nas três subdivisões seguintes."
        ),
        cross_references=("nbr12721:2006:vc3:sec-3.7",),
    )
    sec_37221 = _ref(
        suffix="sec-3.7.2.2.1",
        section="3.7.2.2.1",
        locator=_arabic(11, "3"),
        reference_type="definition_classification",
        description="Classifica vaga vinculada como área acessória da unidade.",
        cross_references=("nbr12721:2006:vc3:sec-3.7.2.2",),
    )
    sec_37222 = _ref(
        suffix="sec-3.7.2.2.2",
        section="3.7.2.2.2",
        locator=_arabic(11, "3"),
        reference_type="definition_classification",
        description="Classifica a vaga constituída como unidade autônoma.",
        cross_references=("nbr12721:2006:vc3:sec-3.7.2.2",),
    )
    sec_37223 = _ref(
        suffix="sec-3.7.2.2.3",
        section="3.7.2.2.3",
        locator=_arabic(12, "4"),
        reference_type="definition_classification",
        description="Classifica vaga de uso comum e indeterminado.",
        cross_references=("nbr12721:2006:vc3:sec-3.7.2.2",),
    )
    sec_373 = _ref(
        suffix="sec-3.7.3",
        section="3.7.3",
        locator=_arabic(12, "4"),
        reference_type="definition_classification",
        description=(
            "Distingue coberta-padrão, coberta de padrão diferente, "
            "descoberta e área equivalente de custo padrão."
        ),
        cross_references=("nbr12721:2006:vc3:sec-3.7",),
    )
    sec_374 = _ref(
        suffix="sec-3.7.4",
        section="3.7.4",
        locator=_arabic(12, "4"),
        reference_type="definition_classification",
        description=(
            "Distingue divisão proporcional e não proporcional de áreas "
            "comuns."
        ),
        cross_references=("nbr12721:2006:vc3:sec-3.7",),
    )
    sec_314 = _ref(
        suffix="sec-3.14",
        section="3.14",
        locator=_arabic(13, "5"),
        reference_type="calculation_distribution",
        description=(
            "Define coeficiente de proporcionalidade pela razão da área "
            "equivalente da unidade pelo total correspondente."
        ),
        cross_references=("nbr12721:2006:vc3:sec-5.8.2",),
    )
    sec_52 = _ref(
        suffix="sec-5.2",
        section="5.2",
        locator=_arabic(15, "7"),
        reference_type="measurement_delimitation",
        description="Critério de delimitação da área real do pavimento.",
    )
    sec_53 = _ref(
        suffix="sec-5.3",
        section="5.3",
        locator=_arabic(15, "7"),
        reference_type="measurement_delimitation",
        description="Critério de área real privativa da unidade autônoma.",
    )
    sec_54 = _ref(
        suffix="sec-5.4",
        section="5.4",
        locator=_arabic(15, "7"),
        reference_type="measurement_delimitation",
        description="Critério de área real de uso comum.",
    )
    sec_55 = _ref(
        suffix="sec-5.5",
        section="5.5",
        locator=_arabic(15, "7"),
        reference_type="measurement_delimitation",
        description="Critério de delimitação de área coberta.",
    )
    sec_56 = _ref(
        suffix="sec-5.6",
        section="5.6",
        locator=_arabic(16, "8"),
        reference_type="measurement_delimitation",
        description="Critério de delimitação de área descoberta.",
    )
    sec_57 = _ref(
        suffix="sec-5.7",
        section="5.7",
        locator=_arabic(16, "8"),
        reference_type="calculation_distribution",
        description="Família de regras de área equivalente e coeficientes.",
    )
    sec_571 = _ref(
        suffix="sec-5.7.1",
        section="5.7.1",
        locator=_arabic(16, "8"),
        reference_type="definition_classification",
        description="Conceituação de área equivalente.",
        cross_references=("nbr12721:2006:vc3:sec-5.7",),
    )
    sec_572 = _ref(
        suffix="sec-5.7.2",
        section="5.7.2",
        locator=_arabic(16, "8"),
        reference_type="calculation_distribution",
        description=(
            "Orientação para obtenção de coeficientes de equivalência a "
            "partir de custo demonstrado."
        ),
        cross_references=("nbr12721:2006:vc3:sec-5.7",),
    )
    sec_573 = _ref(
        suffix="sec-5.7.3",
        section="5.7.3",
        locator=_arabic(16, "8"),
        reference_type="applicability_condition",
        description=(
            "Intervalos de coeficientes médios; o intervalo não autoriza "
            "escolha automática de valor."
        ),
        edition_notes="Continua na página impressa 9 (PDF 17).",
        cross_references=("nbr12721:2006:vc3:sec-5.7",),
    )
    sec_581 = _ref(
        suffix="sec-5.8.1",
        section="5.8.1",
        locator=_arabic(17, "9"),
        reference_type="calculation_distribution",
        description=(
            "Autoridade das colunas 1–18 do Quadro I (áreas por pavimento "
            "e globais)."
        ),
        cross_references=("nbr12721:2006:vc3:annex-a:quadro-i",),
    )
    sec_582 = _ref(
        suffix="sec-5.8.2",
        section="5.8.2",
        locator=_arabic(18, "10"),
        reference_type="calculation_distribution",
        description=(
            "Autoridade das colunas 19–38 do Quadro II e da distribuição "
            "proporcional."
        ),
        cross_references=(
            "nbr12721:2006:vc3:sec-3.14",
            "nbr12721:2006:vc3:annex-a:quadro-ii",
        ),
    )
    sec_583 = _ref(
        suffix="sec-5.8.3",
        section="5.8.3",
        locator=_arabic(19, "11"),
        reference_type="form_table",
        description=(
            "Define o Quadro IV-B como resumo de áreas reais para registro "
            "e escrituração."
        ),
        cross_references=(
            "nbr12721:2006:vc3:sec-5.8.3:iv-b-selection",
            "nbr12721:2006:vc3:annex-a:quadro-iv-b",
        ),
    )
    ivb_sel = _ref(
        suffix="sec-5.8.3:iv-b-selection",
        section="5.8.3 nota de seleção IV-B / IV-B-1",
        locator=_arabic(20, "12"),
        reference_type="applicability_condition",
        description=(
            "Exige substituição exclusiva de IV-B por IV-B-1 quando há "
            "área de terreno de uso exclusivo aplicável."
        ),
        authority_refs=(
            "nbr12721:2006:vc3:sec-5.8.3",
            "nbr12721:2006:vc3:annex-a:quadro-iv-b-1",
        ),
    )
    annex_a = _ref(
        suffix="annex-a",
        section="Anexo A",
        locator=_arabic(71, "63"),
        reference_type="form_table",
        description=(
            "Anexo normativo que apresenta os quadros de áreas e "
            "descritivos, incluindo a regra de substituição IV-B-1."
        ),
    )
    quadro_i = _ref(
        suffix="annex-a:quadro-i",
        section="Anexo A / Quadro I",
        locator=_arabic(73, "65"),
        reference_type="form_table",
        description="Formulário do Quadro I (colunas 1–18).",
        cross_references=("nbr12721:2006:vc3:sec-5.8.1",),
        authority_refs=("nbr12721:2006:vc3:annex-a",),
    )
    quadro_ii = _ref(
        suffix="annex-a:quadro-ii",
        section="Anexo A / Quadro II",
        locator=_arabic(73, "65"),
        reference_type="form_table",
        description="Formulário do Quadro II (colunas 19–38).",
        cross_references=("nbr12721:2006:vc3:sec-5.8.2",),
        authority_refs=("nbr12721:2006:vc3:annex-a",),
    )
    quadro_ivb = _ref(
        suffix="annex-a:quadro-iv-b",
        section="Anexo A / Quadro IV-B",
        locator=_arabic(75, "67"),
        reference_type="form_table",
        description="Formulário do Quadro IV-B (colunas A–G).",
        cross_references=("nbr12721:2006:vc3:sec-5.8.3",),
        authority_refs=("nbr12721:2006:vc3:annex-a",),
    )
    quadro_ivb1 = _ref(
        suffix="annex-a:quadro-iv-b-1",
        section="Anexo A / Quadro IV-B-1",
        locator=_arabic(76, "68"),
        reference_type="form_table",
        description=(
            "Formulário do Quadro IV-B-1 (colunas A–J) para terreno de uso "
            "exclusivo."
        ),
        cross_references=("nbr12721:2006:vc3:sec-5.8.3:iv-b-selection",),
        authority_refs=("nbr12721:2006:vc3:annex-a",),
    )
    return (
        cover,
        preface,
        sec_37,
        sec_3721,
        sec_3722,
        sec_37221,
        sec_37222,
        sec_37223,
        sec_373,
        sec_374,
        sec_314,
        sec_52,
        sec_53,
        sec_54,
        sec_55,
        sec_56,
        sec_57,
        sec_571,
        sec_572,
        sec_573,
        sec_581,
        sec_582,
        sec_583,
        ivb_sel,
        annex_a,
        quadro_i,
        quadro_ii,
        quadro_ivb,
        quadro_ivb1,
    )


def baseline_source_and_references() -> tuple[
    NormativeSource,
    tuple[NormativeReference, ...],
]:
    """Fonte + entradas baseline para montagem do índice."""
    return baseline_normative_source(), baseline_references()