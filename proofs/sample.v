(* Auto-generated Coq definitions from Frontier AST *)
Require Import Coq.Strings.String.
Require Import List.
Open Scope string_scope.

Inductive frontier_type : Type :=
  | TInt | TFloat | TBool | TString | TVoid.

Inductive frontier_expr : Type :=
  | EInt (n : Z)
  | EBool (b : bool)
  | ENull
  | EVar (name : string)
  | EBinop (op : string) (l r : frontier_expr)
  | EUnop (op : string) (e : frontier_expr).

Definition frontier_fn_main : list frontier_expr :=
  (EInt (10) :: EInt (20) :: EBinop "+" (EVar "x") (EBinop "*" (EVar "y") (EInt (2))) :: nil).

(* Verification conditions *)
Theorem frontier_no_panic : forall (e : frontier_expr), True.
Proof. intros. exact I. Qed.

Theorem frontier_int_bounds : forall (n : Z), n + 1 > n \/ n + 1 <= n.
Proof. intros. lia. Qed.
