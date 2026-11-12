"""Register datasets here; each downloader owns its arguments and execution."""

from .assembly101 import Assembly101Downloader
from .breakfast import BreakfastDownloader
from .ha4m import HA4MDownloader
from .ikea_asm import IkeaASMDownloader
from .industreal import IndustRealDownloader
from .repcount import RepCountDownloader
from .fineaction import FineActionDownloader

DOWNLOADERS = {
    downloader.key: downloader
    for downloader in (
        IndustRealDownloader(), Assembly101Downloader(), HA4MDownloader(),
        IkeaASMDownloader(), BreakfastDownloader(), RepCountDownloader(), FineActionDownloader(),
    )
}
