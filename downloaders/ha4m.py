"""HA4M portal adapter; download links are supplied explicitly by the user."""

from .base import DirectArchiveDownloader


class HA4MDownloader(DirectArchiveDownloader):
    key = "ha4m"
    folder_name = "HA4M"
    homepage = "https://baltig.cnr.it/ISP/ha4m"
    description = "HA4M — direct file URL required from the publisher portal/ScienceDB; portal login is not automated"
