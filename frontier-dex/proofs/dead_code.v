(* Coq proof: dead code elimination is semantics-preserving *)
Theorem dead_code_elim_sound :
  forall (prog : program),
    semantics prog = semantics (remove_dead_code prog).
Proof.
  intros prog.
  induction prog; simpl; auto.
Qed.
