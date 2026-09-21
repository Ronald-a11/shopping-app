# Product pictures

Every product and category picture lives in [`products/`](products/) as an
800×600 WebP file, about 7 KB each. They are part of the repository, so the
shop looks the same on every machine and never depends on an outside site.

The file name is the product or category name in lower case with the spaces and
punctuation turned into hyphens — Django's `slugify`:

| Name in the shop | File |
| --- | --- |
| Fresh Tomatoes (1kg) | `fresh-tomatoes-1kg.webp` |
| Water (1.5L) | `water-15l.webp` |
| Meat & Poultry (a category) | `category-meat-poultry.webp` |

`default.webp` is the picture for anything without one of its own.

## Giving a product its picture

```bash
python manage.py add_product_images          # only fills in the blank ones
python manage.py add_product_images --force  # replaces every picture
python manage.py add_product_images --dry-run
```

It looks for the product's own file, then its category's, then `default.webp`.

## Real photographs

When you have photographs of the real shelves, put them in this folder and set
each product's **Image** field in Django admin to
`/static/images/products/<your-file>.jpg`. Without `--force`,
`add_product_images` leaves a picture that is already set alone.

Photographs are better than these drawings — they are only here so the shop
never shows an empty square.

> Earlier versions pulled pictures from Unsplash by URL. That is why the shop
> once showed a gym for toilet paper and a living room for matches: the links
> were guessed from product names, and several were dead. Do not go back to
> linking pictures from other sites.
