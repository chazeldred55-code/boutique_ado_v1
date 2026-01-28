/* global Stripe */

(function () {
  // --- Safe guards ---
  const pkEl = document.getElementById("id_stripe_public_key");
  const csEl = document.getElementById("id_client_secret");
  const form = document.getElementById("payment-form");

  if (!pkEl || !csEl || !form) {
    console.warn("Stripe setup missing: key/secret/form not found.");
    return;
  }

  const stripePublicKey = JSON.parse(pkEl.textContent);
  const clientSecret = JSON.parse(csEl.textContent);

  if (!stripePublicKey || !clientSecret) {
    console.warn("Stripe keys/client secret empty. Check view context + env vars.");
    return;
  }

  // --- Stripe Elements setup ---
  const stripe = Stripe(stripePublicKey);
  const elements = stripe.elements();

  const style = {
    base: {
      color: "#000",
      fontFamily: "inherit",
      fontSize: "16px",
      "::placeholder": { color: "#aab7c4" },
    },
    invalid: {
      color: "#dc3545",
    },
  };

  const card = elements.create("card", { style });
  card.mount("#card-element");

  const errorDiv = document.getElementById("card-errors");
  card.on("change", (event) => {
    if (!errorDiv) return;
    errorDiv.textContent = event.error ? event.error.message : "";
  });

  // Helper: read crispy-rendered fields by their IDs
  function getValueById(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const submitButton = document.getElementById("submit-button");
    if (submitButton) submitButton.disabled = true;
    if (errorDiv) errorDiv.textContent = "";

    const billingDetails = {
      name: getValueById("id_full_name"),
      email: getValueById("id_email"),
      phone: getValueById("id_phone_number"),
      address: {
        line1: getValueById("id_street_address1"),
        line2: getValueById("id_street_address2"),
        city: getValueById("id_town_or_city"),
        state: getValueById("id_county"),
        postal_code: getValueById("id_postcode"),
        country: getValueById("id_country"),
      },
    };

    let result;
    try {
      result = await stripe.confirmCardPayment(clientSecret, {
        payment_method: {
          card: card,
          billing_details: billingDetails,
        },
      });
    } catch (err) {
      if (errorDiv) errorDiv.textContent = "Payment failed. Please try again.";
      if (submitButton) submitButton.disabled = false;
      return;
    }

    if (result.error) {
      if (errorDiv) errorDiv.textContent = result.error.message;
      if (submitButton) submitButton.disabled = false;
      return;
    }

    // If payment succeeded, submit the form to your Django POST handler
    if (result.paymentIntent && result.paymentIntent.status === "succeeded") {
      // Optional (but useful): add the PID to the form for saving on the Order model
      let pidInput = document.getElementById("id_stripe_pid");
      if (!pidInput) {
        pidInput = document.createElement("input");
        pidInput.type = "hidden";
        pidInput.name = "stripe_pid";
        pidInput.id = "id_stripe_pid";
        form.appendChild(pidInput);
      }
      pidInput.value = result.paymentIntent.id;

      form.submit();
      return;
    }

    // Any other status:
    if (errorDiv) errorDiv.textContent = "Payment not completed. Please try again.";
    if (submitButton) submitButton.disabled = false;
  });
})();
