package com.example.payments;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/payments")
public class PaymentController {
    private final PaymentService service;

    public PaymentController(PaymentService service) {
        this.service = service;
    }

    @PostMapping
    public String create(@RequestBody PaymentRequest req) {
        return service.create(req);
    }

    @PostMapping("/{id}/settle")
    public String settle(@PathVariable String id) {
        return service.settle(id);
    }
}
