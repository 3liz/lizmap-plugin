"""Transports between the plugin and the server, used by the synchronisation.

Only WebDAV is available for now, through the Lizmap WebDAV module. Another transport, such as a
REST API in Lizmap Web Client, must implement ``RemoteBackend`` and return the same manifest.
"""
