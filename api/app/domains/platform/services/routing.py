from __future__ import annotations

from dataclasses import dataclass

from app.core.provider_catalog import get_provider
from app.core.provider_catalog.types import ProviderConfig
from app.domains.platform.services.platform_config_snapshot import get_platform_config_snapshot


@dataclass
class RouteResult:
    provider_code: str
    public_model_code: str
    execution_model_code: str
    pricing_strategy: str
    route_group: str
    is_async: bool = False
    is_streaming: bool = False
    fallback_used: bool = False
    provider: ProviderConfig | None = None
    provider_account_id: int | None = None
    provider_account_short_id: str | None = None
    provider_account_owner_type: str | None = None


@dataclass
class RoutePlan:
    route_mode: str
    attempts: list[RouteResult]
    requested_providers: list[str]
    fallback_used: bool = False

    @property
    def route_plan(self) -> list[str]:
        return [attempt.provider_code for attempt in self.attempts]

    @property
    def selected(self) -> RouteResult:
        selected = self.attempts[0]
        selected.fallback_used = self.fallback_used
        return selected


class RoutingError(Exception):
    pass


class ProviderNotFoundError(RoutingError):
    pass


class NoAvailableProviderError(RoutingError):
    pass


class RoutingService:
    def _parse_chain(self, chain: str | None) -> list[str]:
        if not chain:
            return []

        parsed: list[str] = []
        seen_provider_codes: set[str] = set()
        for raw_code in chain.split(","):
            provider_code = raw_code.strip()
            if not provider_code or provider_code in seen_provider_codes:
                continue
            seen_provider_codes.add(provider_code)
            parsed.append(provider_code)
        return parsed

    def list_candidates(self, route_group: str, requested_model: str | None = None) -> list[RouteResult]:
        snapshot = get_platform_config_snapshot()
        candidates: list[RouteResult] = []
        route = None
        if requested_model:
            route = snapshot.routes.get((requested_model, route_group))

        def _append_bindings(model_code: str) -> None:
            for binding in snapshot.list_bindings(model_code, route_group):
                try:
                    provider = get_provider(binding.provider_code)
                except KeyError:
                    continue
                candidates.append(
                    RouteResult(
                        provider_code=binding.provider_code,
                        public_model_code=model_code,
                        execution_model_code=binding.execution_model_code,
                        pricing_strategy=binding.pricing_strategy,
                        route_group=route_group,
                        is_async=binding.is_async,
                        is_streaming=binding.is_streaming,
                        provider=provider,
                    )
                )

        if requested_model:
            if route is None:
                return []
            _append_bindings(requested_model)
            configured_order = {
                provider_code: index
                for index, provider_code in enumerate(route.default_chain)
            }
            candidates.sort(
                key=lambda item: (
                    configured_order.get(item.provider_code, len(configured_order)),
                    item.provider_code,
                )
            )
            return candidates

        for (model_code, binding_route_group), _route in snapshot.routes.items():
            if binding_route_group != route_group:
                continue
            _append_bindings(model_code)
        candidates.sort(key=lambda item: (item.public_model_code, item.provider_code))
        return candidates

    def default_chain(
        self,
        route_group: str,
        requested_model: str | None = None,
        *,
        allow_fallback: bool = True,
    ) -> str | None:
        if not requested_model:
            return None

        snapshot = get_platform_config_snapshot()
        try:
            route = snapshot.get_route(requested_model, route_group)
        except KeyError:
            return None
        configured_chain = list(route.default_chain)
        if not configured_chain:
            return None

        candidates = self.list_candidates(route_group=route_group, requested_model=requested_model)
        if not candidates:
            return None

        candidate_provider_codes = {candidate.provider_code for candidate in candidates}

        provider_codes = [
            provider_code
            for provider_code in configured_chain
            if provider_code in candidate_provider_codes
        ]
        if not allow_fallback and provider_codes:
            provider_codes = provider_codes[:1]

        if not provider_codes:
            return None
        return ",".join(provider_codes)

    def plan(
        self,
        route_group: str,
        requested_model: str | None = None,
        chain: str | None = None,
        allow_fallback: bool = True,
    ) -> RoutePlan:
        snapshot = get_platform_config_snapshot()
        candidates = self.list_candidates(route_group=route_group, requested_model=requested_model)
        if not candidates:
            raise NoAvailableProviderError("no_available_provider")

        candidate_map = {candidate.provider_code: candidate for candidate in candidates}
        requested_chain = self._parse_chain(chain)
        route_mode = "chain" if requested_chain else "default"
        fallback_used = False
        attempts: list[RouteResult] = []
        used_provider_codes: set[str] = set()

        def append_candidate(candidate: RouteResult) -> None:
            if candidate.provider_code in used_provider_codes:
                return
            used_provider_codes.add(candidate.provider_code)
            attempts.append(candidate)

        if requested_chain:
            for provider_code in requested_chain:
                candidate = candidate_map.get(provider_code)
                if candidate is not None:
                    append_candidate(candidate)

            if not attempts:
                raise ProviderNotFoundError("chain_not_found_or_not_supported")
        else:
            if requested_model:
                route = snapshot.get_route(requested_model, route_group)
                configured_chain = [
                    provider_code
                    for provider_code in route.default_chain
                    if provider_code in candidate_map
                ]
                if not configured_chain:
                    raise NoAvailableProviderError("default_chain_not_configured")
                provider_codes = configured_chain if allow_fallback else configured_chain[:1]
                for provider_code in provider_codes:
                    append_candidate(candidate_map[provider_code])
            elif allow_fallback:
                for candidate in candidates:
                    append_candidate(candidate)
            else:
                append_candidate(candidates[0])

        if not attempts:
            raise NoAvailableProviderError("no_available_provider")

        return RoutePlan(
            route_mode=route_mode,
            attempts=attempts,
            requested_providers=requested_chain,
            fallback_used=fallback_used,
        )

    def get_provider(self, provider_code: str):
        return get_provider(provider_code)
