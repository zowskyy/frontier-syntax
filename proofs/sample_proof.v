(* Generated Coq proof for Frontier v2.0 *)
Require Import Arith.

Definition double (x : nat) : nat.
Proof.
  (* Precondition: x > 0 *)
  exact (x * 2).
Defined.

Theorem double_increases : forall x, x > 0 -> double x > x.
Proof.
  intros x Hx.
  unfold double.
  auto.
Qed.
