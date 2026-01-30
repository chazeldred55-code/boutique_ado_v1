import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    endpoint_secret = getattr(settings, "STRIPE_WH_SECRET", "")

    # quick debug
    print("---- STRIPE WEBHOOK HIT ----")
    print("method:", request.method)
    print("path:", request.path)
    print("payload bytes:", len(payload))
    print("sig header present:", bool(sig_header))
    print("wh secret present:", bool(endpoint_secret))
    print("wh secret starts:", (endpoint_secret or "")[:10])

    if not endpoint_secret:
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret,
        )
    except ValueError as e:
        print("❌ ValueError (invalid payload):", e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print("❌ SignatureVerificationError:", e)
        return HttpResponse(status=400)

    print("✅ event type:", event["type"])

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        print("✅ payment_intent.succeeded:", intent.get("id"))

    elif event["type"] == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        print("❌ payment_intent.payment_failed:", intent.get("id"))

    return HttpResponse(status=200)
