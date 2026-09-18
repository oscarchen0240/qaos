from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services import folders as svc

router = APIRouter(prefix="/api/folders", tags=["folders"])


class FolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class FolderPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class Item(BaseModel):
    group_key: str
    testcase_id: str


class ItemsIn(BaseModel):
    items: list[Item]


@router.get("")
def list_folders():
    return svc.list_all()


@router.post("", status_code=201)
def create_folder(body: FolderIn):
    return svc.create(body.name, body.description)


@router.patch("/{fid}")
def patch_folder(fid: int, body: FolderPatch):
    return svc.rename(fid, body.name, body.description)


@router.delete("/{fid}", status_code=204)
def delete_folder(fid: int):
    svc.delete(fid)


@router.post("/{fid}/items")
def add_items(fid: int, body: ItemsIn):
    return svc.add_items(fid, [i.model_dump() for i in body.items])


@router.delete("/{fid}/items")
def remove_items(fid: int, body: ItemsIn):
    return svc.remove_items(fid, [i.model_dump() for i in body.items])
