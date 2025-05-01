import datetime
from CTFd.cache import cache
from CTFd.models import Solves

from . import force_cache_updates, get_all_containers

@cache.memoize(timeout=1200, forced_update=force_cache_updates)
def get_container_stats():
    containers = get_all_containers()
    return [{attr: container.labels[f"dojo.{attr}_id"]
            for attr in ["dojo", "module", "challenge"]}
            for container in containers]


@cache.memoize(timeout=1200, forced_update=force_cache_updates)
def get_dojo_stats(dojo):
    return dict(
        users=dojo.solves().group_by(Solves.user_id).count(),
        challenges=len(dojo.challenges),
        visible_challenges=len([challenge for challenge in dojo.challenges if challenge.visible()]),
        solves=dojo.solves().count(),
    )

def get_full_container_stats():
    containers = get_all_containers()
    enriched_stats = []

    for container in containers:
        try:
            stats = container.stats(stream=False)

            mem_usage = stats.get("memory_stats", {}).get("usage", 0)
            mem_limit = stats.get("memory_stats", {}).get("limit", 1)
            mem_percent = (mem_usage / mem_limit) * 100 if mem_limit else 0

            created = container.attrs.get("Created", "").split(".")[0]
            uptime = str(datetime.datetime.now() - datetime.datetime.fromisoformat(created)) if created else "N/A"

            enriched_stats.append({
                "id": container.id,
                "name": container.name,
                "image": container.image.tags,
                "status": container.status,
                "created": created,
                "uptime": uptime,
                "labels": container.labels,
                "mem_usage": mem_usage,
                "mem_limit": mem_limit,
                "mem_percent": round(mem_percent, 2),
            })

        except Exception as e:
            print(f"Failed to process container {container.id}: {e}")
            continue

    return enriched_stats

