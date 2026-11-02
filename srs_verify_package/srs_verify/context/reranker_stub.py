"""精排器stub: 包内未vendor BGE-Reranker, 触发即降级直通."""


class BgeReranker:  # noqa: D101
    def __init__(self) -> None:
        raise ImportError(
            'BgeReranker未vendor进srs_verify包; '
            '召回走直通序(精排增益见repo内algorithms版本)')
