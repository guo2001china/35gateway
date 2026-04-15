from typing import Any

import httpx


class BaseProviderAdapter:
    def require_provider_model(self, ctx: dict[str, Any]) -> Any:
        provider_model = ctx.get("provider_model")
        if provider_model is None:
            raise httpx.HTTPError("provider_model_missing")
        return provider_model

    def require_public_model_code(self, ctx: dict[str, Any]) -> str:
        public_model_code = self.resolve_public_model_code(ctx)
        if isinstance(public_model_code, str) and public_model_code:
            return public_model_code
        raise httpx.HTTPError("provider_model_public_model_code_missing")

    def require_execution_model_code(self, ctx: dict[str, Any]) -> str:
        execution_model_code = self.resolve_execution_model_code(ctx)
        if isinstance(execution_model_code, str) and execution_model_code:
            return execution_model_code
        raise httpx.HTTPError("provider_model_execution_model_code_missing")

    def resolve_public_model_code(self, ctx: dict[str, Any]) -> str | None:
        provider_model = ctx.get("provider_model")
        if provider_model is not None:
            public_model_code = getattr(provider_model, "public_model_code", None)
            if isinstance(public_model_code, str) and public_model_code:
                return public_model_code
            legacy_model_code = getattr(provider_model, "model_code", None)
            if isinstance(legacy_model_code, str) and legacy_model_code:
                return legacy_model_code

        public_model_code = ctx.get("public_model")
        if isinstance(public_model_code, str) and public_model_code:
            return public_model_code
        return None

    def resolve_execution_model_code(self, ctx: dict[str, Any]) -> str | None:
        provider_model = ctx.get("provider_model")
        if provider_model is not None:
            execution_model_code = getattr(provider_model, "execution_model_code", None)
            if isinstance(execution_model_code, str) and execution_model_code:
                return execution_model_code
            legacy_model_code = getattr(provider_model, "model_code", None)
            if isinstance(legacy_model_code, str) and legacy_model_code:
                return legacy_model_code
        return None

    def require_route_group(self, ctx: dict[str, Any]) -> str:
        route_group = ctx.get("route_group")
        if isinstance(route_group, str) and route_group:
            return route_group
        provider_model = self.require_provider_model(ctx)
        route_group = getattr(provider_model, "route_group", None)
        if isinstance(route_group, str) and route_group:
            return route_group
        raise httpx.HTTPError("provider_model_route_group_missing")

    def build_request(self, ctx: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def parse_response(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        raise NotImplementedError

    def parse_error(self, ctx: dict[str, Any], resp: Any) -> dict[str, Any]:
        raise NotImplementedError

    def create_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def query_task(self, ctx: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def fetch_content(self, ctx: dict[str, Any]) -> tuple[bytes, str | None]:
        raise NotImplementedError

    async def invoke(self, ctx: dict[str, Any]) -> Any:
        raise NotImplementedError
