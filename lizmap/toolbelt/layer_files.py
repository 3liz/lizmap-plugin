#
# QGis sidecar files utilities
#
from pathlib import Path
from typing import (
    Iterator,
    Set,
)

from qgis.core import (
    QgsMapLayer,
    QgsProject,
    QgsProviderMetadata,
    QgsProviderRegistry,
)

NETWORK_VSI_PREFIXES = (
    "/vsicurl/",
    "/vsicurl_streaming/",
    "/vsis3/",
    "/vsigs/",
    "/vsiaz/",
    "/vsiadls/",
    "/vsioss/",
    "/vsiswift/",
    "/vsihdfs/",
    "/vsiwebhdfs/",
)


def layer_local_path(
    registry: QgsProviderRegistry,
    layer: QgsMapLayer,
    provider_name: str,
) -> tuple[Path, QgsProviderMetadata] | None:
    """Check if the layer is local file based"""
    md = registry.providerMetadata(provider_name)

    if md is None or not (md.providerCapabilities() & QgsProviderMetadata.ProviderCapability.FileBasedUris):
        return None

    components = registry.decodeUri(provider_name, layer.source())
    path = components.get("path")
    if not path:
        return None

    if components.get("vsiPrefix", "") in NETWORK_VSI_PREFIXES:
        return None

    if "://" in path:
        # Plain remote URL handed to GDAL, no /vsicurl/ prefix
        return None

    try:
        path = Path(path)
        if path.is_file():
            # Connection string (PG:, MySQL:), or a missing file QGIS already warns about
            return (path, md)
    except OSError:
        # https://github.com/3liz/lizmap-plugin/issues/541 — WinError 123
        pass

    return None


def scan_layer_files(
    project: QgsProject,
    *,
    included_provider: Set[str] | None = None,
    excluded_providers: Set[str] | None = None,
) -> Iterator[tuple[QgsMapLayer, Path, list[Path]]]:
    """Return an iterator over layer file resourc path
    and the list of sidecar files associated

    Only valid for file based layers.
    """
    registry = QgsProviderRegistry.instance()

    for layer in project.mapLayers().values():
        provider = layer.dataProvider()
        if provider is None:
            continue

        provider_name = provider.name()

        if included_provider is not None and provider_name not in included_provider:
            continue

        if excluded_providers is not None and provider_name in excluded_providers:
            continue

        if (local_path_data := layer_local_path(registry, layer, provider_name)) is not None:
            path, md = local_path_data

            # gdal provider always provide the same bunch of unecessary auxiliary files
            # *.vat.dbf, *.aux.xml, *.ovr, *.wld
            if provider_name == "gdal":
                yield (layer, path, [])
                continue

            yield (
                layer,
                path,
                [p for file in md.sidecarFilesForUri(str(path)) if (p := Path(file)).is_file()],
            )
