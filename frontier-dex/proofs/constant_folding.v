(* Coq proof: constant folding preserves semantics *)
Theorem constant_folding_sound :
  forall (e1 e2 : expr),
    eval e1 = eval e2 ->
    eval (fold_constants e1) = eval e2.
Proof.
  intros e1 e2 H.
  induction e1; simpl; auto.
Qed.
