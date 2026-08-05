(*
  Frontier v2.0: Verified Proof for double Function
*)

Require Import Arith.
Require Import Lia.

Definition double (x : nat) : nat := x + x.

Theorem double_preserves_positive : forall x : nat, x > 0 -> double x > 0.
Proof.
  intros x Hx.
  unfold double.
  lia.
Qed.

Theorem double_increases : forall x : nat, x > 0 -> double x > x.
Proof.
  intros x Hx.
  unfold double.
  lia.
Qed.

Theorem double_commutes : forall x y : nat,
  double (x + y) = double x + double y.
Proof.
  intros x y.
  unfold double.
  lia.
Qed.

Theorem double_zero : double 0 = 0.
Proof.
  unfold double.
  reflexivity.
Qed.

Definition frontier_double_contract (x : nat) : nat :=
  match x with
  | 0 => 0
  | S n => S (S (double n))
  end.

Theorem frontier_double_correct : forall x : nat,
  frontier_double_contract x = double x.
Proof.
  intros x.
  destruct x as [|n].
  - reflexivity.
  - simpl. unfold double. lia.
Qed.
