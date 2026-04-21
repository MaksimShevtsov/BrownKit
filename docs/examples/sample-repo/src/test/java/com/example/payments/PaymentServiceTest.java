package com.example.payments;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class PaymentServiceTest {
    @Test
    void settleReturnsMarker() {
        var s = new PaymentService();
        assertEquals("p1:settled", s.settle("p1"));
    }
}
