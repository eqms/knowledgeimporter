# Release Notes

## Version 0.4.0 (25.02.2026)

### Added
- Universal Document Converter foundation: `BaseConverter` ABC with `RawDocument`, `Section`, `ValidationResult`, `ConversionResult` data models and YAML frontmatter generation
- New dependencies for Universal Converter: `pandas`, `openpyxl`, `pyyaml`, `lxml`, `chardet`
- Document conversion support: PDF, DOCX, HTML, ODT → Markdown via markitdown and odfdo

### Changed
- Replaced log UI with file-based logging; removed dead code for app icon
- Updated CLAUDE.md with FilePicker documentation for Flet 0.80+
- Threading fixes, loading spinner and icon improvements (v0.2.1)

### Fixed
- Replaced `Container min_height` with `height` for Flet 0.80+ compatibility
- Registered FilePicker as service instead of control (Flet 0.80+ requirement)
