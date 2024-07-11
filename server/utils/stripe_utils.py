from typing import List
from models.ItemModel import ItemModel


async def capitalize_first_letter(word: str) -> str:
    if word:
        return word[0].upper() + word[1:]
    else:
        return word

# async def convert_checkout_to_item(checkout_models: List[SingleCheckoutModel]):
#     item_models = []

#     for checkout_model in checkout_models:
#         color = await capitalize_first_letter(checkout_model.color)
#         apparel = await capitalize_first_letter(checkout_model.apparel)

#         item_model = ItemModel(
#             apparel=apparel,
#             size=checkout_model.size,
#             color=color,
#             img_id=checkout_model.img_id,
#             prompt=checkout_model.prompt,
#             thumbnail=checkout_model.thumbnail,
#             toggled=checkout_model.toggled,
#         )
#         item_models.append(item_model)
#     return item_models