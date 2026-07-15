Vendored from [Moist-Cat/synack](https://github.com/Moist-Cat/synack) at commit `47e69b2f80ccb286c6d399dcfb368a3ce0d326a1`.

Local changes:
- converted imports to package-relative imports for vendoring under `src/vendor/synack`
- removed eager package config import
- made OpenTelemetry optional so parsing works without exporter/runtime dependencies
