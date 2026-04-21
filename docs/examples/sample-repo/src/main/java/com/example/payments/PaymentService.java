package com.example.payments;

import java.time.LocalDateTime;

public class PaymentService {
    public String create(PaymentRequest req) {
        var now = LocalDateTime.now();
        return "pay_" + now.toString();
    }

    public String settle(String id) {
        return id + ":settled";
    }
}

class PaymentRequest {
    public String customerId;
    public long amountCents;
    public String currency;
}
