export type CartItem = {
  variantId: string;
  productName: string;
  productSlug: string;
  variantName: string;
  priceMinor: number;
  quantity: number;
};

export type DeliveryArea = {
  id: string;
  name: string;
  fee_minor: number;
  currency: "NGN";
};

export type CheckoutResponse = {
  order_number: string;
  order_status: "AWAITING_PAYMENT";
  payment_status: "PENDING";
  reservation_expires_at: string;
  summary: {
    subtotal_minor: number;
    delivery_fee_minor: number;
    total_minor: number;
    currency: "NGN";
  };
  payment_url: string;
  order_access_token: string;
  idempotent_replay: boolean;
};
