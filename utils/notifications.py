import logging
from functools import singledispatch
from typing import Any
from typing import Dict

from little_boxes import activitypub as ap

from config import DB
from config import MetaKey
from config import _meta
from utils.meta import by_actor
from utils.meta import by_type
from utils.meta import in_inbox
from utils.meta import not_undo

_logger = logging.getLogger(__name__)

_NewMeta = Dict[str, Any]


@singledispatch
def set_inbox_flags(activity: ap.BaseActivity, new_meta: _NewMeta) -> None:
    return None


@set_inbox_flags.register
def _accept_set_inbox_flags(activity: ap.Accept, new_meta: _NewMeta) -> None:
    """Handle notifications for "accepted" following requests."""
    _logger.info(f"set_inbox_flags activity={activity!r}")
    # Check if this actor already follow us back
    follows_back = False
    follow_query = {
        **in_inbox(),
        **by_type(ap.ActivityType.FOLLOW),
        **by_actor(activity.get_actor()),
        **not_undo(),
    }
    raw_follow = DB.activities.find_one(follow_query)
    if raw_follow:
        follows_back = True

        DB.activities.update_many(
            follow_query, {"$set": {_meta(MetaKey.NOTIFICATION_FOLLOWS_BACK): True}}
        )

    # This Accept will be a "You started following $actor" notification
    new_meta.update(
        **{
            _meta(MetaKey.NOTIFICATION): True,
            _meta(MetaKey.NOTIFICATION_UNREAD): True,
            _meta(MetaKey.NOTIFICATION_FOLLOWS_BACK): follows_back,
        }
    )
    return None


@set_inbox_flags.register
def _follow_set_inbox_flags(activity: ap.Follow, new_meta: _NewMeta) -> None:
    """Handle notification for new followers."""
    # Check if we're already following this actor
    follows_back = False
    accept_query = {
        **in_inbox(),
        **by_type(ap.ActivityType.ACCEPT),
        **by_actor(activity.get_actor()),
        **not_undo(),
    }
    raw_accept = DB.activities.find_one(accept_query)
    if raw_accept:
        follows_back = True

        DB.activities.update_many(
            accept_query, {"$set": {_meta(MetaKey.NOTIFICATION_FOLLOWS_BACK): True}}
        )

    # This Follow will be a "$actor started following you" notification
    new_meta.update(
        **{
            _meta(MetaKey.NOTIFICATION): True,
            _meta(MetaKey.NOTIFICATION_UNREAD): True,
            _meta(MetaKey.NOTIFICATION_FOLLOWS_BACK): follows_back,
        }
    )
    return None