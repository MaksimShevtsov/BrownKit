package com.example.customers;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/customers")
public class CustomerController {
    private final CustomerRepository repo;

    public CustomerController(CustomerRepository repo) {
        this.repo = repo;
    }

    @GetMapping("/{id}")
    public String get(@PathVariable String id) {
        return repo.find(id);
    }
}
