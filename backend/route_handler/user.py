from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from backend.db.dal import (
    DALPhotobookBookmarks,
    DALPhotobooks,
    DAOPhotobookBookmarksCreate,
    FilterOp,
    OrderDirection,
    safe_commit,
)
from backend.db.externals import (
    PhotobookBookmarksOverviewResponse,
    PhotobooksOverviewResponse,
)
from backend.route_handler.base import RouteHandler


class UserBookmarkPhotobookInputPayload(BaseModel):
    photobook_id: UUID
    source_analytics: Optional[str] = None


class UserGetPhotobooksResponse(BaseModel):
    photobooks: list[PhotobooksOverviewResponse]


class UserAPIHandler(RouteHandler):
    def register_routes(self) -> None:
        self.router.add_api_route(
            "/api/user/{user_id}/photobooks",
            self.user_get_photobooks,
            methods=["GET"],
            response_model=UserGetPhotobooksResponse,
        )
        self.router.add_api_route(
            "/api/user/{user_id}/photobooks/bookmarks",
            self.user_get_bookmarked_photobooks,
            methods=["GET"],
            response_model=UserGetPhotobooksResponse,
        )
        self.router.add_api_route(
            "/api/user/{user_id}/photobooks/bookmark_new",
            self.user_photobook_bookmark_new,
            methods=["POST"],
            response_model=PhotobookBookmarksOverviewResponse,
        )

    async def user_get_photobooks(
        self,
        user_id: UUID,
    ) -> UserGetPhotobooksResponse:
        async with self.app.new_db_session() as db_session:
            photobooks = await DALPhotobooks.list_all(
                db_session,
                {"user_id": (FilterOp.EQ, user_id)},
                order_by=[("updated_at", OrderDirection.DESC)],
            )
            resp = UserGetPhotobooksResponse(
                photobooks=await PhotobooksOverviewResponse.rendered_from_daos(
                    photobooks, db_session, self.app.asset_manager
                )
            )
            return resp

    async def user_get_bookmarked_photobooks(
        self, user_id: UUID
    ) -> UserGetPhotobooksResponse:
        async with self.app.new_db_session() as db_session:
            photobook_bookmarks = await DALPhotobookBookmarks.list_all(
                db_session,
                {"user_id": (FilterOp.EQ, user_id)},
                order_by=[("created_at", OrderDirection.DESC)],
            )
            photobooks = await DALPhotobooks.get_by_ids(
                db_session, [bookmark.photobook_id for bookmark in photobook_bookmarks]
            )
            return UserGetPhotobooksResponse(
                photobooks=await PhotobooksOverviewResponse.rendered_from_daos(
                    photobooks, db_session, self.app.asset_manager
                )
            )

    async def user_photobook_bookmark_new(
        self,
        user_id: UUID,
        payload: UserBookmarkPhotobookInputPayload,
    ) -> PhotobookBookmarksOverviewResponse:
        async with self.app.new_db_session() as db_session:
            async with safe_commit(db_session):
                dao = await DALPhotobookBookmarks.create(
                    db_session,
                    DAOPhotobookBookmarksCreate(
                        user_id=user_id,
                        photobook_id=payload.photobook_id,
                        source=payload.source_analytics,
                    ),
                )
            return PhotobookBookmarksOverviewResponse.from_dao(dao)
