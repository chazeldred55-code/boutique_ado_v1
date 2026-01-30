from django.shortcuts import render, redirect, reverse, get_object_or_404, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.template.loader import render_to_string

import stripe

from .forms import OrderForm
from .models import Order, OrderLineItem
from products.models import Product
from bag.context_processors import bag_contents


def checkout(request):
    """
    Display checkout page + create Stripe PaymentIntent (GET)
    Process order form + save order/line items (POST)
    """
    # ✅ Debug in the correct place (request exists here)
    print("CHECKOUT VIEW HIT:", request.method)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Bag check
    bag = request.session.get("bag", {})
    if not bag:
        messages.error(request, "There's nothing in your bag at the moment")
        return redirect(reverse("products"))

    # Bag totals (use your context processor so delivery etc matches the site)
    current_bag = bag_contents(request)
    grand_total = current_bag["grand_total"]
    stripe_total = round(grand_total * 100)  # pounds -> pence

    # -------------------------
    # POST: create the Order
    # -------------------------
    if request.method == "POST":
        form_data = {
            "full_name": request.POST.get("full_name"),
            "email": request.POST.get("email"),
            "phone_number": request.POST.get("phone_number"),
            "country": request.POST.get("country"),
            "postcode": request.POST.get("postcode"),
            "town_or_city": request.POST.get("town_or_city"),
            "street_address1": request.POST.get("street_address1"),
            "street_address2": request.POST.get("street_address2"),
            "county": request.POST.get("county"),
        }
        order_form = OrderForm(form_data)

        if order_form.is_valid():
            order = order_form.save(commit=False)

            # Grab client_secret from the hidden input (Stripe injects it on page)
            client_secret = request.POST.get("client_secret", "")
            # client_secret looks like: "pi_xxx_secret_yyy"
            stripe_pid = client_secret.split("_secret")[0] if "_secret" in client_secret else ""
            order.stripe_pid = stripe_pid

            order.original_bag = bag  # if your Order model uses JSONField this is fine
            order.save()

            # Create line items
            try:
                for item_id, item_data in bag.items():
                    product = get_object_or_404(Product, pk=item_id)

                    # If you use sizes/variants (dict), handle both cases
                    if isinstance(item_data, int):
                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                    else:
                        # e.g. {"items_by_size": {"s": 1, "m": 2}}
                        for size, quantity in item_data.get("items_by_size", {}).items():
                            OrderLineItem.objects.create(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )

            except Exception as e:
                print("ERROR creating line items:", e)
                order.delete()
                messages.error(request, "Sorry, there was a problem processing your order.")
                return redirect(reverse("view_bag"))

            # Clear bag
            request.session["bag"] = {}

            # Send confirmation email (simple + safe for dev)
            try:
                subject = f"Order Confirmation - {order.order_number}"
                message = render_to_string(
                    "checkout/confirmation_emails/confirmation_email_body.txt",
                    {"order": order, "contact_email": settings.DEFAULT_FROM_EMAIL},
                )
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [order.email],
                )
                # if your model has email_sent boolean
                if hasattr(order, "email_sent"):
                    order.email_sent = True
                    order.save(update_fields=["email_sent"])
            except Exception as e:
                print("EMAIL SEND ERROR:", e)
                # Don't block checkout if email fails in dev

            return redirect(reverse("checkout_success", args=[order.order_number]))
        else:
            messages.error(
                request,
                "There was an error with your form. Please double check your information.",
            )

    # -------------------------
    # GET: show checkout + intent
    # -------------------------
    else:
        order_form = OrderForm()

        try:
            intent = stripe.PaymentIntent.create(
                amount=stripe_total,
                currency=settings.STRIPE_CURRENCY,
            )
        except Exception as e:
            print("STRIPE INTENT ERROR:", e)
            messages.error(request, "Sorry, our payment system is unavailable right now.")
            return redirect(reverse("view_bag"))

        client_secret = intent.client_secret

    template = "checkout/checkout.html"
    context = {
        "order_form": order_form,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
        "client_secret": client_secret,
    }
    return render(request, template, context)


def checkout_success(request, order_number):
    """
    Display checkout success page
    """
    order = get_object_or_404(Order, order_number=order_number)
    messages.success(request, f"Order successfully processed! Your order number is {order_number}.")
    return render(request, "checkout/checkout_success.html", {"order": order})
