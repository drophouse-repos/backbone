import base64
import pytest

# import asyncio
from unittest.mock import AsyncMock, MagicMock
from routers.imagen import (
    like_image,
    unlike_image,
    record_prompt_and_image,
    processAndSaveImage,
)
from botocore.exceptions import NoCredentialsError
from models.BrowsedImageDataModel import (
    BrowsedImageData,
)  # Replace 'your_model_module' with the actual model module name


# Mock DatabaseOperations class
class MockDatabaseOperations:
    async def add_liked_image(self, user_id, image_data):
        pass

    async def remove_liked_image(self, user_id, image_data):
        pass

    async def add_browsed_image(self, user_id, image_data):
        pass

    async def add_to_cart(self, user_id, cart_items):
        pass

    async def remove_from_cart(self, user_id, item_id):
        pass


class MockBoto3Client:
    def upload_fileobj(self, fileobj, bucket_name, key):
        pass


@pytest.mark.asyncio
async def test_like_image_success():
    db_obj = MockDatabaseOperations()
    db_obj.add_liked_image = AsyncMock(return_value=True)
    img_id = "test_img_id"
    user_id = "test_user"
    assert await like_image(img_id, db_obj, user_id)


@pytest.mark.asyncio
async def test_like_image_failure():
    db_obj = MockDatabaseOperations()
    db_obj.add_liked_image = AsyncMock(side_effect=Exception("DB Error"))
    img_id = "test_img_id"
    user_id = "test_user"
    with pytest.raises(Exception):
        await like_image(img_id, db_obj, user_id)


@pytest.mark.asyncio
async def test_unlike_image_success():
    db_obj = MockDatabaseOperations()
    db_obj.remove_liked_image = AsyncMock(return_value=True)
    img_id = "test_img_id"
    user_id = "test_user"
    assert await unlike_image(img_id, db_obj, user_id)


@pytest.mark.asyncio
async def test_unlike_image_failure():
    db_obj = MockDatabaseOperations()
    db_obj.remove_liked_image = AsyncMock(side_effect=Exception("DB Error"))
    img_id = "test_img_id"
    user_id = "test_user"
    with pytest.raises(Exception):
        await unlike_image(img_id, db_obj, user_id)


@pytest.mark.asyncio
async def test_record_prompt_and_image_success():
    db_obj = MockDatabaseOperations()
    db_obj.add_browsed_image = AsyncMock(return_value=True)
    browsed_data = MagicMock(spec=BrowsedImageData)
    browsed_data.img_id = "test_img_id"
    user_id = "test_user"
    with open("server\\tests\\test_image.jpg", "rb") as image_file:
        test_string = base64.b64encode(image_file.read()).decode("utf-8")
    assert await record_prompt_and_image(test_string, browsed_data, db_obj, user_id)


@pytest.mark.asyncio
async def test_record_prompt_and_image_failure():
    db_obj = MockDatabaseOperations()
    db_obj.add_browsed_image = AsyncMock(side_effect=Exception("DB Error"))
    browsed_data = MagicMock(spec=BrowsedImageData)
    browsed_data.img_id = "test_img_id"
    user_id = "test_user"
    # image = "image_base64_string"
    with open("server\\tests\\test_image.jpg", "rb") as image_file:
        test_string = base64.b64encode(image_file.read()).decode("utf-8")
    with pytest.raises(Exception):
        await record_prompt_and_image(test_string, browsed_data, db_obj, user_id)


def test_processAndSaveImage_success(mocker):
    mocker.patch("boto3.client", return_value=MockBoto3Client())
    with open("server\\tests\\test_image.jpg", "rb") as image_file:
        test_string = base64.b64encode(image_file.read()).decode("utf-8")
    assert processAndSaveImage(test_string, "img_id")


def test_processAndSaveImage_failure(mocker):
    mocker.patch("boto3.client", side_effect=NoCredentialsError)
    with pytest.raises(Exception):
        processAndSaveImage("image_base64_string", "img_id")
