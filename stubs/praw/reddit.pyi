from typing import Optional, Dict, Any

from . import models

class Reddit:
    def __init__(self,
                 site_name: Optional[str]=None,
                 requestor_class: Optional[Any]=None,
                 requestor_kwargs: Optional[Dict[str, Any]]=None,
                 **config_settings: Any) -> None: ...

    subreddit = ... # type: models.SubredditHelper
