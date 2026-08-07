(* Coq proof: control flow recovery matches original CFG *)
Theorem control_flow_recovery :
  forall (cfg recovered : control_graph),
    valid_recovery cfg recovered ->
    reachable cfg = reachable recovered.
Proof.
  intros cfg recovered H.
  destruct H; reflexivity.
Qed.
