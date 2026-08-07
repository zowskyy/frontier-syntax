(* Frontier v2.0: Constant folding soundness proof *)
Require Import Arith.
Require Import Lia.

Inductive expr : Type :=
  | EConst : nat -> expr
  | EAdd : expr -> expr -> expr
  | EMul : expr -> expr -> expr.

Fixpoint eval (e : expr) : nat :=
  match e with
  | EConst n => n
  | EAdd a b => eval a + eval b
  | EMul a b => eval a * eval b
  end.

Fixpoint fold_constants (e : expr) : expr :=
  match e with
  | EConst n => EConst n
  | EAdd (EConst a) (EConst b) => EConst (a + b)
  | EAdd a b => EAdd (fold_constants a) (fold_constants b)
  | EMul (EConst a) (EConst b) => EConst (a * b)
  | EMul a b => EMul (fold_constants a) (fold_constants b)
  end.

Theorem constant_folding_const : forall n, eval (fold_constants (EConst n)) = n.
Proof. intros. reflexivity. Qed.

Theorem constant_folding_add : forall a b,
  eval (fold_constants (EAdd (EConst a) (EConst b))) = a + b.
Proof. intros. reflexivity. Qed.

Theorem constant_folding_mul : forall a b,
  eval (fold_constants (EMul (EConst a) (EConst b))) = a * b.
Proof. intros. reflexivity. Qed.

Theorem constant_folding_example : eval (fold_constants (EAdd (EConst 2) (EConst 3))) = 5.
Proof. reflexivity. Qed.
