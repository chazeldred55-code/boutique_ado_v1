from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.http import HttpResponse
from products.models import Product


def view_bag(request):
    """Render the bag contents page."""
    return render(request, "bag/bag.html")


def add_to_bag(request, item_id):
    """Add a quantity of the specified product to the shopping bag."""
    product = get_object_or_404(Product, pk=item_id)
    quantity = int(request.POST.get("quantity"))
    redirect_url = request.POST.get("redirect_url")

    size = None
    if "product_size" in request.POST:
        size = request.POST["product_size"]

    bag = request.session.get("bag", {})

    # Products WITH sizes
    if size:
        if item_id in bag:
            if size in bag[item_id]["items_by_size"]:
                bag[item_id]["items_by_size"][size] += quantity
                messages.success(
                    request,
                    f"Updated {product.name} size {size.upper()} quantity to "
                    f"{bag[item_id]['items_by_size'][size]}."
                )
            else:
                bag[item_id]["items_by_size"][size] = quantity
                messages.success(
                    request,
                    f"Added {product.name} size {size.upper()} to your bag."
                )
        else:
            bag[item_id] = {"items_by_size": {size: quantity}}
            messages.success(
                request,
                f"Added {product.name} size {size.upper()} to your bag."
            )

    # Products WITHOUT sizes
    else:
        if item_id in bag:
            bag[item_id] += quantity
            messages.success(
                request,
                f"Updated {product.name} quantity to {bag[item_id]}."
            )
        else:
            bag[item_id] = quantity
            messages.success(
                request,
                f"Added {product.name} to your bag."
            )

    request.session["bag"] = bag
    return redirect(redirect_url)


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product to the specified amount."""
    product = get_object_or_404(Product, pk=item_id)
    quantity = int(request.POST.get("quantity"))

    size = None
    if "product_size" in request.POST:
        size = request.POST["product_size"]

    bag = request.session.get("bag", {})

    # Products WITH sizes
    if size:
        if quantity > 0:
            bag[item_id]["items_by_size"][size] = quantity
            messages.success(
                request,
                f"Updated {product.name} size {size.upper()} quantity to {quantity}."
            )
        else:
            bag[item_id]["items_by_size"].pop(size, None)
            messages.success(
                request,
                f"Removed {product.name} size {size.upper()} from your bag."
            )
            if not bag[item_id]["items_by_size"]:
                bag.pop(item_id, None)

    # Products WITHOUT sizes
    else:
        if quantity > 0:
            bag[item_id] = quantity
            messages.success(
                request,
                f"Updated {product.name} quantity to {quantity}."
            )
        else:
            bag.pop(item_id, None)
            messages.success(
                request,
                f"Removed {product.name} from your bag."
            )

    request.session["bag"] = bag
    return redirect(reverse("view_bag"))


def remove_from_bag(request, item_id):
    """
    Remove an item from the bag.
    If the item has sizes, remove only the specified size (POST: product_size).
    Otherwise remove the entire item.
    Designed to be called via AJAX and return HTTP 200 on success.
    """
    product = get_object_or_404(Product, pk=item_id)
    bag = request.session.get("bag", {})
    size = request.POST.get("product_size")

    try:
        if size:
            bag[item_id]["items_by_size"].pop(size, None)
            if not bag[item_id]["items_by_size"]:
                bag.pop(item_id, None)
            messages.success(
                request,
                f"Removed {product.name} size {size.upper()} from your bag."
            )
        else:
            bag.pop(item_id, None)
            messages.success(
                request,
                f"Removed {product.name} from your bag."
            )

        request.session["bag"] = bag
        return HttpResponse(status=200)

    except Exception:
        return HttpResponse(status=500)
