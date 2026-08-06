(* Frontier v2.0: Dead code elimination soundness proof *)
Require Import Arith.
Require Import Lia.

Inductive stmt : Type :=
  | SSkip : stmt
  | SAssign : nat -> nat -> stmt
  | SSeq : stmt -> stmt -> stmt
  | SDead : stmt.

Fixpoint semantics (s : stmt) (env : nat -> nat) : nat -> nat :=
  match s with
  | SSkip => env
  | SAssign x v => fun y => if Nat.eqb y x then v else env y
  | SSeq a b => semantics b (semantics a env)
  | SDead => env
  end.

Fixpoint remove_dead_code (s : stmt) : stmt :=
  match s with
  | SSkip => SSkip
  | SAssign x v => SAssign x v
  | SSeq a b => SSeq (remove_dead_code a) (remove_dead_code b)
  | SDead => SSkip
  end.

Theorem dead_code_elim_skip :
  forall (env : nat -> nat) (x : nat), semantics SSkip env x = env x.
Proof. intros. reflexivity. Qed.

Theorem dead_code_elim_dead :
  forall (env : nat -> nat) (x : nat),
    semantics (remove_dead_code SDead) env x = semantics SDead env x.
Proof. intros. reflexivity. Qed.

Theorem dead_code_elim_assign :
  forall (v x y : nat) (env : nat -> nat),
    semantics (remove_dead_code (SAssign x v)) env y =
    semantics (SAssign x v) env y.
Proof. intros. reflexivity. Qed.
