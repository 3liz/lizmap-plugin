"""
__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'
"""


from qgis.core import QgsDataSourceUri

from lizmap.saas import _update_ssl

from .compat import TestCase


class TestSaas(TestCase):

    def test_ssl_update(self):
        """ Test we can update an SSL connection. """
        uri = QgsDataSourceUri(
            'dbname=\'database\' host=a-host.com port=5432 user=\'admin@admin\' password=\'passWORD\' '
            'sslmode=disable key=\'id\' estimatedmetadata=true srid=4326 type=MultiPoint '
            'checkPrimaryKeyUnicity=\'1\' table="demo"."point" (geom)'
        )
        self.assertEqual(QgsDataSourceUri.SslMode.SslDisable, uri.sslMode())

        new_ssl = QgsDataSourceUri.SslMode.SslPrefer
        new_uri = _update_ssl(uri, new_ssl)
        self.assertEqual(new_ssl, new_uri.sslMode())

        new_ssl = QgsDataSourceUri.SslMode.SslRequire
        new_uri = _update_ssl(uri, new_ssl)
        self.assertEqual(new_ssl, new_uri.sslMode())

    def test_ssl_update_force(self):
        """ Test we can update an SSL connection by forcing. """
        uri = QgsDataSourceUri(
            'dbname=\'database\' host=a-host.com port=5432 user=\'admin@admin\' password=\'passWORD\' '
            'key=\'id\' estimatedmetadata=true srid=4326 type=MultiPoint '
            'checkPrimaryKeyUnicity=\'1\' table="demo"."point" (geom)'
        )
        self.assertEqual(QgsDataSourceUri.SslMode.SslPrefer, uri.sslMode())

        new_ssl = QgsDataSourceUri.SslMode.SslRequire
        new_uri = _update_ssl(uri, new_ssl, True)
        self.assertEqual(new_ssl, new_uri.sslMode())
