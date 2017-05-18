from typing import Optional, Dict, Any

from . import models

class Reddit:
    def __init__(self,
                 site_name: Optional[str]=None,
                 **config_settings: Any) -> None: ...

    subreddit = ... # type: models.SubredditHelper
