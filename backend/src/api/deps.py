from fastapi import Request

from src.container import Container


def get_container_from_request(request: Request) -> Container:
    return request.state.container
