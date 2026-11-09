import pytest

from confpilot_es.normalizer import normalize, variants


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("and R.R.F. to rank the results", "and rrf to rank the results"),
        ("and r r f to rank the results", "and rrf to rank the results"),
        ("it uses BM 25 for that", "it uses bm25 for that"),
        ("it uses bm twenty five for that", "it uses bm25 for that"),
        ("It uses BM25 for keyword matches", "it uses bm25 for keyword matches"),
        ("retrieval-augmented generation is common", "retrieval augmented generation is common"),
        ("the user's K 8 s cluster", "the users k8s cluster"),
        ("a pod goes into CrashLoopBackOff", "a pod goes into crashloopbackoff"),
        ("", ""),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_variants_keep_the_unjoined_form() -> None:
    # The aggressive join must never hide a plain match such as "kubernetes".
    assert variants("Kubernetes 1.30 is out") == ["kubernetes 1 30 is out", "kubernetes1 30 is out"]
    assert variants("managed hybrid search") == ["managed hybrid search"]
