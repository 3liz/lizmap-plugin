"""Tests for the sidecar files utilities in lizmap.toolbelt.layer_files."""

from pathlib import Path
from zipfile import ZipFile

import pytest

from qgis.core import (
    Qgis,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from lizmap.toolbelt.layer_files import layer_local_path, scan_layer_files


@pytest.fixture()
def registry() -> QgsProviderRegistry:
    return QgsProviderRegistry.instance()


@pytest.fixture()
def project() -> QgsProject:
    """A standalone project, not the singleton one."""
    project = QgsProject()
    yield project
    project.clear()


@pytest.fixture()
def shapefile(data: Path, tmp_path: Path) -> Path:
    """Write a shapefile, which comes with its own sidecar files."""
    source = QgsVectorLayer(str(data.joinpath("points.geojson")), "points", "ogr")
    assert source.isValid()

    destination = tmp_path.joinpath("points.shp")
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "ESRI Shapefile"
    error, message = QgsVectorFileWriter.writeAsVectorFormatV3(
        source,
        str(destination),
        QgsCoordinateTransformContext(),
        options,
    )[0:2]
    assert error == QgsVectorFileWriter.WriterError.NoError, message
    return destination


@pytest.fixture()
def zipped_shapefile(shapefile: Path, tmp_path: Path) -> Path:
    """Zip the shapefile, so it can be read through the /vsizip/ prefix."""
    archive = tmp_path.joinpath("archive.zip")
    with ZipFile(archive, "w") as zip_file:
        for path in shapefile.parent.glob("points.*"):
            zip_file.write(path, path.name)
    return archive


def vector_layer(uri: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(uri, "layer", "ogr")
    assert layer.isValid(), uri
    return layer


def raster_layer(uri: str) -> QgsRasterLayer:
    layer = QgsRasterLayer(uri, "layer", "gdal")
    assert layer.isValid(), uri
    return layer


#
# layer_local_path()
#


def test_local_vector(registry, data):
    """Test a local vector file is detected."""
    path = data.joinpath("points.geojson")
    layer = vector_layer(str(path))

    result = layer_local_path(registry, layer, "ogr")

    assert result is not None
    assert result[0] == path
    assert result[1].key() == "ogr"


def test_local_geopackage(registry, data):
    """Test the container is returned, not the URI with the layer name."""
    path = data.joinpath("points_lines.gpkg")
    layer = vector_layer(f"{path}|layername=points")

    result = layer_local_path(registry, layer, "ogr")

    assert result is not None
    assert result[0] == path


def test_local_raster(registry, data):
    """Test a local raster file is detected."""
    path = data.joinpath("raster.asc")
    layer = raster_layer(str(path))

    result = layer_local_path(registry, layer, "gdal")

    assert result is not None
    assert result[0] == path
    assert result[1].key() == "gdal"


def test_memory_layer(registry):
    """Test a provider which is not file based is discarded."""
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "memory", "memory")
    assert layer.isValid()

    assert layer_local_path(registry, layer, "memory") is None


def test_unknown_provider(registry, data):
    """Test an unknown provider is discarded."""
    layer = vector_layer(str(data.joinpath("points.geojson")))

    assert layer_local_path(registry, layer, "not_an_existing_provider") is None


def test_uri_without_path(registry):
    """Test an URI which can be decoded but without any path is discarded."""
    layer = QgsRasterLayer(
        "crs=EPSG:2056&"
        "dpiMode=7&"
        "format=image/jpeg&"
        "layers=ch.swisstopo.pixelkarte-grau&"
        "styles&"
        "url=https://wms.geo.admin.ch/",
        "wms",
        "wms",
    )
    assert layer.isValid()

    assert layer_local_path(registry, layer, "wms") is None


def test_network_vsi_prefix(registry, data):
    """Test a COG behind a network VSI prefix is discarded."""
    # The layer itself does not need to be reachable, only its source is inspected
    layer = raster_layer(str(data.joinpath("raster.asc")))
    layer.setDataSource(
        "/vsicurl/https://demo.snap.lizmap.com/lizmap/cog/raster.tif",
        "cog",
        "gdal",
    )

    assert layer_local_path(registry, layer, "gdal") is None


def test_local_vsi_prefix(registry, zipped_shapefile):
    """Test a local VSI prefix, /vsizip/, is not discarded as a network one."""
    layer = vector_layer(f"/vsizip/{zipped_shapefile}/points.shp")

    result = layer_local_path(registry, layer, "ogr")

    assert result is not None
    assert result[0] == zipped_shapefile


def test_plain_remote_url(registry, data):
    """Test a remote URL handed to GDAL without any VSI prefix is discarded."""
    layer = raster_layer(str(data.joinpath("raster.asc")))
    layer.setDataSource("https://demo.snap.lizmap.com/lizmap/cog/raster.tif", "cog", "gdal")

    assert layer_local_path(registry, layer, "gdal") is None


def test_missing_file(registry, data, tmp_path):
    """Test a layer pointing to a file which does not exist is discarded."""
    layer = vector_layer(str(data.joinpath("points.geojson")))
    layer.setDataSource(str(tmp_path.joinpath("does_not_exist.geojson")), "missing", "ogr")

    assert layer_local_path(registry, layer, "ogr") is None


def test_directory_is_not_a_file(registry, data, tmp_path):
    """Test a layer pointing to a directory is discarded."""
    layer = vector_layer(str(data.joinpath("points.geojson")))
    layer.setDataSource(str(tmp_path), "directory", "ogr")

    assert layer_local_path(registry, layer, "ogr") is None


#
# scan_layer_files()
#


def test_empty_project(project):
    """Test an empty project does not yield anything."""
    assert list(scan_layer_files(project)) == []


def test_only_file_based_layers(project, data):
    """Test only file based layers are yielded."""
    vector = vector_layer(str(data.joinpath("points.geojson")))
    memory = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "memory", "memory")
    project.addMapLayers([vector, memory])

    results = list(scan_layer_files(project))

    assert len(results) == 1
    layer, path, sidecar_files = results[0]
    assert layer.id() == vector.id()
    assert path == data.joinpath("points.geojson")
    assert sidecar_files == []


def test_same_file_used_twice(project, data):
    """Test a file used by two layers is yielded twice, the caller deduplicates."""
    path = data.joinpath("points.geojson")
    project.addMapLayers([vector_layer(str(path)), vector_layer(str(path))])

    results = list(scan_layer_files(project))

    assert [result[1] for result in results] == [path, path]


def test_included_provider(project, data):
    """Test the filter on included providers."""
    project.addMapLayers(
        [
            vector_layer(str(data.joinpath("points.geojson"))),
            raster_layer(str(data.joinpath("raster.asc"))),
        ]
    )

    results = list(scan_layer_files(project, included_provider={"gdal"}))

    assert [result[1] for result in results] == [data.joinpath("raster.asc")]


def test_excluded_providers(project, data):
    """Test the filter on excluded providers."""
    project.addMapLayers(
        [
            vector_layer(str(data.joinpath("points.geojson"))),
            raster_layer(str(data.joinpath("raster.asc"))),
        ]
    )

    results = list(scan_layer_files(project, excluded_providers={"gdal"}))

    assert [result[1] for result in results] == [data.joinpath("points.geojson")]


def test_both_filters(project, data):
    """Test both filters at the same time, the exclusion wins."""
    project.addMapLayer(vector_layer(str(data.joinpath("points.geojson"))))

    results = scan_layer_files(project, included_provider={"ogr"}, excluded_providers={"ogr"})

    assert list(results) == []


def test_sidecar_files(project, shapefile):
    """Test the sidecar files of a shapefile which are existing on the disk."""
    project.addMapLayer(vector_layer(str(shapefile)))

    results = list(scan_layer_files(project))

    assert len(results) == 1
    _, path, sidecar_files = results[0]
    assert path == shapefile

    # Apparently no .prj file is generated with QGIS <= 3.34
    if Qgis.versionInt() < 34000:
        expected = {shapefile.with_suffix(suffix) for suffix in (".shx", ".dbf", ".cpg")}
    else:
        expected = {shapefile.with_suffix(suffix) for suffix in (".shx", ".dbf", ".prj", ".cpg")}
    assert set(sidecar_files) == expected
    # Only existing files must be returned, sidecarFilesForUri() returns candidates
    assert all(sidecar.is_file() for sidecar in sidecar_files)


def test_gdal_sidecar_files_are_skipped(project, data):
    """Test the auxiliary files of the GDAL provider are never returned."""
    # raster.asc comes with raster.asc.aux.xml and raster.prj in the data folder
    assert data.joinpath("raster.asc.aux.xml").is_file()
    project.addMapLayer(raster_layer(str(data.joinpath("raster.asc"))))

    results = list(scan_layer_files(project))

    assert len(results) == 1
    assert results[0][2] == []
