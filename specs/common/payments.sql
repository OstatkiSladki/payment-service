-- PAYMENT SERVICE - db_payment
-- Таблицы: payments, promo_codes, promo_code_usages

CREATE SCHEMA IF NOT EXISTS "public";

CREATE TYPE "public"."payment_method" AS ENUM ('bank_card', 'sbp');
CREATE TYPE "public"."payment_status" AS ENUM ('pending', 'succeeded', 'failed', 'refunded', 'partially_refunded');


CREATE TABLE "public"."payments" (
    "id" BIGSERIAL PRIMARY KEY,
    "order_id" BIGINT NOT NULL,  
    "transaction_id" VARCHAR(255) NOT NULL UNIQUE,
    "payment_gateway" VARCHAR(50) NOT NULL,
    "amount" DECIMAL(10, 2) NOT NULL,
    "refunded_amount" DECIMAL(10, 2) DEFAULT 0.00,
    "currency" VARCHAR(3) DEFAULT 'RUB',
    "status" payment_status DEFAULT 'pending',
    "payment_method" payment_method,
    "gateway_response" JSONB DEFAULT '{}',
    "failure_reason" TEXT,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    "paid_at" TIMESTAMP WITH TIME ZONE,
    "refunded_at" TIMESTAMP WITH TIME ZONE
);
CREATE INDEX "payments_idx_order" ON "public"."payments" ("order_id");
CREATE INDEX "payments_idx_transaction" ON "public"."payments" ("transaction_id");
CREATE INDEX "payments_idx_status" ON "public"."payments" ("status");


CREATE TABLE "public"."promo_codes" (
    "id" BIGSERIAL PRIMARY KEY,
    "code" VARCHAR(50) NOT NULL UNIQUE,
    "discount_type" VARCHAR(20) NOT NULL,
    "discount_value" DECIMAL(10, 2) NOT NULL,
    "min_order_amount" DECIMAL(10, 2) DEFAULT 0.00,
    "valid_until" TIMESTAMP WITH TIME ZONE,
    "is_active" BOOLEAN DEFAULT TRUE,
    "rules_json" JSONB DEFAULT '{}',
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX "promo_codes_idx_code" ON "public"."promo_codes" ("code", "is_active");


CREATE TABLE "public"."promo_code_usages" (
    "id" BIGSERIAL PRIMARY KEY,
    "promo_code_id" BIGINT NOT NULL,
    "user_id" BIGINT NOT NULL,  
    "order_id" BIGINT,  
    "discount_applied" DECIMAL(10, 2) NOT NULL,
    "created_at" TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "fk_pcu_promo" FOREIGN KEY ("promo_code_id") REFERENCES "public"."promo_codes"("id") ON DELETE CASCADE
);
CREATE INDEX "promo_code_usages_idx_user" ON "public"."promo_code_usages" ("user_id", "promo_code_id");
CREATE INDEX "promo_code_usages_idx_order" ON "public"."promo_code_usages" ("order_id");
