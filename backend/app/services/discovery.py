import logging
import re
from urllib.parse import quote, unquote

from playwright.async_api import Page
from sqlmodel import Session, select

from app.database import engine
from app.models import ActivityLog, ActionType, Blacklist, Lead, LeadStatus, Niche
from app.services.browser import get_browser_page
from app.utils.jitter import human_pause

logger = logging.getLogger(__name__)

TIKTOK_BASE = "https://www.tiktok.com"

NICHE_KEYWORDS = (
    "academia",
    "academy",
    "gym",
    "gimnasio",
    "estudio",
    "studio",
    "clases",
    "classes",
    "danza",
    "dance",
    "ballet",
    "pilates",
    "yoga",
    "fitness",
    "entrenamiento",
    "coach",
    "entrenador",
    "alumnos",
    "deporte",
    "baile",
    "crossfit",
    "workout",
)

_SEARCH_USER_CARD_SELECTORS = [
    '[data-e2e="search-user-card"]',
    '[data-e2e="user-card"]',
    'div[class*="DivUserCard"]',
    'div[class*="UserCard"]',
    'li[class*="UserItem"]',
    'div[class*="user-item"]',
]

_USERNAME_LINK_SELECTORS = [
    'a[href*="/@"]',
    'a[data-e2e="search-user-link"]',
    'span[class*="UniqueId"] a',
]

_BIO_SELECTORS = [
    '[data-e2e="user-bio"]',
    '[data-e2e="user-desc"]',
    'div[class*="DivShareDesc"]',
    'div[class*="BioText"]',
    'span[class*="Bio"]',
]

_FOLLOWER_SELECTORS = [
    '[data-e2e="followers-count"]',
    '[data-e2e="user-card-followers-count"]',
    'strong[title*="Followers" i]',
    'div[class*="FollowCount"] span',
    'span[class*="follow"]',
]

_DISPLAY_NAME_SELECTORS = [
    '[data-e2e="user-title"]',
    '[data-e2e="user-subtitle"]',
    'h1',
    'h2[class*="nickname"]',
    'span[class*="Name"]',
]

_SCROLL_TARGET_SELECTORS = [
    'div[class*="DivUserListContainer"]',
    'div[class*="DivSearchListContainer"]',
    'main',
    'div[id="main-content"]',
]


def parse_follower_count(text: str) -> int | None:
    if not text:
        return None
    t = text.strip().upper().replace(",", "").replace(" ", "")
    t = re.sub(r"[^\d.KM]", "", t)
    try:
        if "M" in t:
            num = re.sub(r"[^\d.]", "", t.split("M")[0])
            if not num:
                return None
            return int(float(num) * 1_000_000)
        if "K" in t:
            num = re.sub(r"[^\d.]", "", t.split("K")[0])
            if not num:
                return None
            return int(float(num) * 1_000)
        digits = re.sub(r"[^\d]", "", t)
        return int(digits) if digits else None
    except (ValueError, TypeError):
        return None


def _username_from_href(href: str) -> str | None:
    if not href or "/@" not in href:
        return None
    m = re.search(r"/@([^/?#]+)", href)
    if not m:
        return None
    u = m.group(1).strip()
    if not u:
        return None
    skip = {
        "foryou",
        "following",
        "live",
        "messages",
        "explore",
        "search",
        "tag",
    }
    if u.lower() in skip:
        return None
    return unquote(u)


async def safe_text(scope: Page, selectors: list[str]) -> str:
    for sel in selectors:
        try:
            loc = scope.locator(sel).first
            if await loc.count() > 0:
                text = await loc.inner_text()
                if text and text.strip():
                    return text.strip()
        except Exception:
            continue
    return ""


def _bio_matches_niche(bio: str) -> bool:
    b = bio.lower()
    return any(kw in b for kw in NICHE_KEYWORDS)


def _infer_niche(bio: str) -> Niche:
    b = bio.lower()
    if any(x in b for x in ("danza", "dance", "ballet", "baile")):
        return Niche.danza
    if any(x in b for x in ("futbol", "soccer", "fútbol")):
        return Niche.futbol
    if "pilates" in b:
        return Niche.pilates
    if "gym" in b or "gimnasio" in b or "crossfit" in b:
        return Niche.gym
    if "yoga" in b:
        return Niche.yoga
    if any(x in b for x in ("karate", "jiu", "mma", "boxeo", "lucha")):
        return Niche.artes_marciales
    if any(x in b for x in ("música", "musica", "piano", "violin")):
        return Niche.musica
    return Niche.otros


def _log_discovery(lead_id: int | None, message: str, action: ActionType = ActionType.discovered):
    with Session(engine) as session:
        session.add(
            ActivityLog(
                job_id=None,
                lead_id=lead_id,
                level="info",
                message=message[:500],
                action_type=action,
            )
        )
        session.commit()


async def _scroll_search_results(page: Page, iterations: int) -> None:
    for _ in range(iterations):
        for sel in _SCROLL_TARGET_SELECTORS:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.evaluate("el => el.scrollBy(0, 900)")
                    await human_pause(1.2, 2.8)
                    return
            except Exception:
                continue
        await page.mouse.wheel(0, 800)
        await human_pause(1.2, 2.8)


async def _collect_usernames_from_search(page: Page, target: int) -> list[str]:
    seen: set[str] = set()
    order: list[str] = []
    max_rounds = min(80, max(15, target // 2 + 10))

    for _ in range(max_rounds):
        if len(order) >= target:
            break

        for card_sel in _SEARCH_USER_CARD_SELECTORS:
            try:
                cards = page.locator(card_sel)
                n = await cards.count()
                for i in range(n):
                    card = cards.nth(i)
                    for link_sel in _USERNAME_LINK_SELECTORS:
                        links = card.locator(link_sel)
                        lc = await links.count()
                        for j in range(lc):
                            href = await links.nth(j).get_attribute("href")
                            u = _username_from_href(href or "")
                            if u and u.lower() not in seen:
                                seen.add(u.lower())
                                order.append(u)
                            if len(order) >= target:
                                break
                        if len(order) >= target:
                            break
                    if len(order) >= target:
                        break
            except Exception:
                continue

        if len(order) >= target:
            break

        links = await page.locator('a[href*="/@"]').all()
        for link in links:
            href = await link.get_attribute("href")
            u = _username_from_href(href or "")
            if u and u.lower() not in seen:
                seen.add(u.lower())
                order.append(u)
            if len(order) >= target:
                break

        if len(order) >= target:
            break

        await _scroll_search_results(page, 1)

    return order[:target]


async def _extract_profile_fields(page: Page, username: str) -> dict:
    url = f"{TIKTOK_BASE}/@{username}"
    out: dict = {
        "username": username,
        "profile_url": url,
        "bio": "",
        "business_name": "",
        "follower_count": None,
    }
    await page.goto(url, wait_until="networkidle", timeout=45_000)
    await human_pause(2.0, 5.0)

    out["bio"] = await safe_text(page, _BIO_SELECTORS)
    out["business_name"] = await safe_text(page, _DISPLAY_NAME_SELECTORS)
    raw_followers = await safe_text(page, _FOLLOWER_SELECTORS)
    out["follower_count"] = parse_follower_count(raw_followers)

    return out


def _qualify(follower_count: int | None, bio: str) -> tuple[LeadStatus, str | None]:
    if follower_count is None:
        return LeadStatus.excluded, "No califica: seguidores no legibles"
    if follower_count < 500:
        return LeadStatus.excluded, f"No califica: {follower_count} seguidores (<500)"
    if not _bio_matches_niche(bio):
        return LeadStatus.excluded, "No califica: bio sin keywords de nicho"
    return LeadStatus.qualified, None


async def discover_leads(hashtag: str, limit: int = 50) -> dict:
    tag = hashtag.strip().lstrip("#")
    if not tag:
        return {"error": "empty_hashtag", "saved": 0, "hashtag": hashtag}

    page = None
    saved = 0
    skipped = 0
    errors: list[str] = []

    try:
        page = await get_browser_page()
        q = quote(tag, safe="")
        url = f"{TIKTOK_BASE}/search/user?q={q}"
        await page.goto(url, wait_until="networkidle", timeout=45_000)
        await human_pause(3.0, 6.0)

        collect_target = min(500, max(limit * 3, limit + 20))
        usernames = await _collect_usernames_from_search(page, collect_target)

        for username in usernames:
            if saved >= limit:
                break

            with Session(engine) as session:
                bl = session.exec(
                    select(Blacklist).where(Blacklist.username == username)
                ).first()
                if bl:
                    skipped += 1
                    continue
                existing = session.exec(
                    select(Lead).where(Lead.username == username)
                ).first()
                if existing:
                    skipped += 1
                    continue

            await human_pause(2.0, 5.0)

            try:
                info = await _extract_profile_fields(page, username)
            except Exception as e:
                err = f"@{username}: {e}"
                logger.warning(err)
                errors.append(err)
                continue

            fc = info.get("follower_count")
            bio = info.get("bio") or ""
            status, exclude_reason = _qualify(fc, bio)
            niche = _infer_niche(bio) if status == LeadStatus.qualified else Niche.otros
            notes = exclude_reason if status == LeadStatus.excluded else None

            with Session(engine) as session:
                lead = Lead(
                    username=username,
                    business_name=info.get("business_name") or None,
                    profile_url=info.get("profile_url", f"{TIKTOK_BASE}/@{username}"),
                    niche=niche,
                    follower_count=fc,
                    bio=bio or None,
                    status=status,
                    notes=notes,
                )
                session.add(lead)
                session.commit()
                session.refresh(lead)

            saved += 1
            msg = f"Discovery #{tag}: @{username} → {status.value}"
            _log_discovery(lead.id, msg, ActionType.qualified if status == LeadStatus.qualified else ActionType.excluded)

        logger.info(f"Discovery #{tag}: saved={saved} skipped={skipped}")
        return {
            "hashtag": tag,
            "saved": saved,
            "skipped": skipped,
            "errors": errors[:20],
        }

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        _log_discovery(None, f"Discovery error #{tag}: {e}", ActionType.error)
        return {"error": str(e), "saved": saved, "hashtag": tag, "errors": errors}

    finally:
        if page and not page.is_closed():
            try:
                await page.close()
            except Exception:
                pass
