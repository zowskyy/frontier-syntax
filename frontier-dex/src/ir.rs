use crate::parser::{ClassMethod, CodeItem, DexFile};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct SsaValue(pub u32);

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SsaOperand {
    Register(u16),
    Value(SsaValue),
    ConstI32(i32),
    ConstWide(i64),
    String(String),
    Type(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SsaInstruction {
    Nop,
    Const { dest: u16, value: SsaOperand },
    Move { dest: u16, src: SsaOperand },
    Add { dest: u16, left: SsaOperand, right: SsaOperand },
    Return { value: Option<SsaOperand> },
    ReturnVoid,
    Goto { target: u32 },
    If {
        cond: IfCondition,
        left: SsaOperand,
        right: SsaOperand,
        target: u32,
    },
    Invoke {
        kind: InvokeKind,
        method: String,
        args: Vec<SsaOperand>,
        result: Option<u16>,
    },
    Phi {
        dest: u16,
        inputs: Vec<(u32, SsaOperand)>,
    },
    Switch {
        discriminant: SsaOperand,
        targets: Vec<(i32, u32)>,
        default: u32,
    },
    Raw { opcode: u16, words: Vec<u16> },
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum IfCondition {
    Eq,
    Ne,
    Lt,
    Ge,
    Gt,
    Le,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub enum InvokeKind {
    Virtual,
    Static,
    Direct,
    Interface,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BasicBlock {
    pub id: u32,
    pub start_pc: u32,
    pub end_pc: u32,
    pub instructions: Vec<SsaInstruction>,
    pub successors: Vec<u32>,
    pub predecessors: Vec<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SsaFunction {
    pub name: String,
    pub registers: u16,
    pub blocks: HashMap<u32, BasicBlock>,
    pub entry: u32,
    pub phi_count: usize,
}

pub struct Disassembler;

impl Disassembler {
    pub fn disassemble_method(class_name: &str, method: &ClassMethod) -> Option<SsaFunction> {
        let code = method.code.as_ref()?;
        let mut blocks = build_cfg(code);
        insert_phi_nodes(&mut blocks);
        let phi_count = blocks
            .values()
            .flat_map(|b| b.instructions.iter())
            .filter(|i| matches!(i, SsaInstruction::Phi { .. }))
            .count();
        Some(SsaFunction {
            name: format!("{class_name}::{}", method.name),
            registers: code.registers_size,
            blocks,
            entry: 0,
            phi_count,
        })
    }

    pub fn disassemble_all(dex: &DexFile) -> Vec<SsaFunction> {
        let mut functions = Vec::new();
        for class in &dex.classes {
            for method in &class.methods {
                if let Some(f) = Self::disassemble_method(&class.class_name, method) {
                    functions.push(f);
                }
            }
        }
        functions
    }
}

fn build_cfg(code: &CodeItem) -> HashMap<u32, BasicBlock> {
    let insns = &code.insns;
    let mut leaders = HashSet::new();
    leaders.insert(0u32);
    let mut pc = 0usize;
    while pc < insns.len() {
        let opcode = (insns[pc] & 0xFF) as u8;
        let width = opcode_width(opcode, insns, pc);
        match opcode {
            0x28 => {
                if pc + 1 < insns.len() {
                    let offset = insns[pc + 1] as i16 as i32;
                    let target = (pc as i32 + offset) as u32;
                    if target < insns.len() as u32 {
                        leaders.insert(target);
                    }
                }
                leaders.insert((pc + width) as u32);
            }
            0x32..=0x3d => {
                if pc + 2 < insns.len() {
                    let offset = insns[pc + 2] as i16 as i32;
                    let target = (pc as i32 + offset) as u32;
                    if target < insns.len() as u32 {
                        leaders.insert(target);
                    }
                }
                leaders.insert((pc + width) as u32);
            }
            0x2b | 0x2c => {
                leaders.insert((pc + width) as u32);
            }
            0x0f => {}
            _ => {}
        }
        pc += width;
    }
    leaders.insert(insns.len() as u32);

    let mut sorted: Vec<u32> = leaders.into_iter().collect();
    sorted.sort_unstable();

    let mut blocks = HashMap::new();
    for (idx, &start) in sorted.iter().enumerate() {
        if start as usize >= insns.len() {
            continue;
        }
        let end = sorted.get(idx + 1).copied().unwrap_or(insns.len() as u32);
        let mut instructions = Vec::new();
        let mut pc = start as usize;
        let mut successors = Vec::new();
        while (pc as u32) < end && pc < insns.len() {
            let (insn, width, branch_target) = decode_insn(insns, pc);
            instructions.push(insn);
            if let Some(tgt) = branch_target {
                successors.push(tgt);
            }
            pc += width;
        }
        if successors.is_empty() && (end as usize) < insns.len() {
            successors.push(end);
        }
        blocks.insert(
            start,
            BasicBlock {
                id: start,
                start_pc: start,
                end_pc: end,
                instructions,
                successors,
                predecessors: Vec::new(),
            },
        );
    }

    let block_ids: Vec<u32> = blocks.keys().copied().collect();
    for id in block_ids.clone() {
        let succs = blocks.get(&id).map(|b| b.successors.clone()).unwrap_or_default();
        for succ in succs {
            if let Some(block) = blocks.get_mut(&succ) {
                if !block.predecessors.contains(&id) {
                    block.predecessors.push(id);
                }
            }
        }
    }
    blocks
}

fn insert_phi_nodes(blocks: &mut HashMap<u32, BasicBlock>) {
    for block in blocks.values_mut() {
        if block.predecessors.len() < 2 {
            continue;
        }
        let mut used_regs = HashSet::new();
        for insn in &block.instructions {
            collect_regs(insn, &mut used_regs);
        }
        for reg in used_regs {
            let inputs: Vec<(u32, SsaOperand)> = block
                .predecessors
                .iter()
                .map(|pred| (*pred, SsaOperand::Register(reg)))
                .collect();
            block.instructions.insert(
                0,
                SsaInstruction::Phi {
                    dest: reg,
                    inputs,
                },
            );
        }
    }
}

fn collect_regs(insn: &SsaInstruction, regs: &mut HashSet<u16>) {
    match insn {
        SsaInstruction::Const { dest, .. }
        | SsaInstruction::Move { dest, .. }
        | SsaInstruction::Add { dest, .. }
        | SsaInstruction::Phi { dest, .. } => {
            regs.insert(*dest);
        }
        SsaInstruction::Invoke { result, .. } => {
            if let Some(r) = result {
                regs.insert(*r);
            }
        }
        _ => {}
    }
}

fn opcode_width(opcode: u8, insns: &[u16], pc: usize) -> usize {
    match opcode {
        0x00 => 1,
        0x01..=0x0d => 1,
        0x0e => 2,
        0x0f => 1,
        0x10..=0x17 => 1,
        0x18..=0x1d => 2,
        0x1e..=0x21 => 1,
        0x22..=0x25 => 2,
        0x28 => 2,
        0x29..=0x2a => 1,
        0x2b | 0x2c => {
            if pc + 1 < insns.len() {
                let size = insns[pc + 1] as usize;
                2 + size * 2
            } else {
                2
            }
        }
        0x32..=0x3d => 3,
        0x3e..=0x43 => 1,
        0x44..=0x51 => 2,
        0x52..=0x5f => 2,
        0x60..=0x6d => 2,
        0x6e..=0x72 => 3,
        0x74..=0x78 => 3,
        0x7b..=0x8f => 2,
        0x90..=0xaf => 1,
        0xb0..=0xcf => 2,
        0xd0..=0xd7 => 3,
        0xe0..=0xe2 => 3,
        _ => 1,
    }
}

fn decode_insn(insns: &[u16], pc: usize) -> (SsaInstruction, usize, Option<u32>) {
    let opcode = (insns[pc] & 0xFF) as u8;
    let width = opcode_width(opcode, insns, pc);
    match opcode {
        0x00 => (SsaInstruction::Nop, width, None),
        0x0e => {
            let value = insns[pc + 1] as i16 as i32;
            let reg = (insns[pc] >> 8) as u16;
            (
                SsaInstruction::Const {
                    dest: reg,
                    value: SsaOperand::ConstI32(value as i32),
                },
                width,
                None,
            )
        }
        0x0f => (SsaInstruction::ReturnVoid, width, None),
        0x11 => {
            let reg = (insns[pc] >> 8) as u16;
            (
                SsaInstruction::Return {
                    value: Some(SsaOperand::Register(reg)),
                },
                width,
                None,
            )
        }
        0x28 => {
            let offset = insns[pc + 1] as i16 as i32;
            let target = (pc as i32 + offset) as u32;
            (
                SsaInstruction::Goto { target },
                width,
                Some(target),
            )
        }
        0x32 => {
            let reg_a = (insns[pc] >> 8) as u16;
            let reg_b = (insns[pc] & 0xFF) as u16;
            let offset = insns[pc + 2] as i16 as i32;
            let target = (pc as i32 + offset) as u32;
            (
                SsaInstruction::If {
                    cond: IfCondition::Eq,
                    left: SsaOperand::Register(reg_a),
                    right: SsaOperand::Register(reg_b),
                    target,
                },
                width,
                Some(target),
            )
        }
        0x6e => {
            let args_reg = (insns[pc] >> 8) as u16;
            (
                SsaInstruction::Invoke {
                    kind: InvokeKind::Virtual,
                    method: format!("invoke@{}", insns[pc + 1]),
                    args: vec![SsaOperand::Register(args_reg)],
                    result: None,
                },
                width,
                None,
            )
        }
        0x90 => {
            let dest = (insns[pc] >> 8) as u16;
            let left = ((insns[pc] >> 4) & 0x0f) as u16;
            let right = (insns[pc] & 0x0f) as u16;
            (
                SsaInstruction::Add {
                    dest,
                    left: SsaOperand::Register(left),
                    right: SsaOperand::Register(right),
                },
                width,
                None,
            )
        }
        0x2b => {
            let reg = (insns[pc] >> 8) as u16;
            let size = insns[pc + 1] as usize;
            let mut targets = Vec::new();
            let mut i = 0;
            while i < size && pc + 2 + i * 2 + 1 < insns.len() {
                let key = insns[pc + 2 + i * 2] as i32;
                let off = insns[pc + 2 + i * 2 + 1] as i16 as i32;
                targets.push((key, (pc as i32 + off) as u32));
                i += 1;
            }
            (
                SsaInstruction::Switch {
                    discriminant: SsaOperand::Register(reg),
                    targets,
                    default: (pc + width) as u32,
                },
                width,
                None,
            )
        }
        _ => (
            SsaInstruction::Raw {
                opcode: opcode as u16,
                words: insns[pc..pc + width].to_vec(),
            },
            width,
            None,
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parser::{parse_code_item, ClassMethod};

    fn sample_code() -> CodeItem {
        let insns = vec![
            0x030e, 0x000a, // const/16 v3, #10
            0x0390,         // add-int v2, v3, v0
            0x000f,         // return-void
        ];
        CodeItem {
            registers_size: 4,
            ins_size: 0,
            outs_size: 0,
            tries_size: 0,
            debug_info_off: 0,
            insns_size: insns.len() as u32,
            insns,
        }
    }

    #[test]
    fn test_disassemble_method() {
        let method = ClassMethod {
            method_idx: 0,
            access_flags: 0,
            code_off: 0,
            name: "foo".into(),
            code: Some(sample_code()),
        };
        let func = Disassembler::disassemble_method("LTest;", &method).unwrap();
        assert!(!func.blocks.is_empty());
    }

    #[test]
    fn test_cfg_branch() {
        let insns = vec![
            0x3200, 0x0000, 0x0003, // if-eq v0,v0, +3 (to pc 6)
            0x000f,                 // return-void at pc 3
            0x0028, 0xfffd,         // goto -3 at pc 4 (back to pc 3)
            0x000f,                 // return-void at pc 6
        ];
        let code = CodeItem {
            registers_size: 2,
            ins_size: 0,
            outs_size: 0,
            tries_size: 0,
            debug_info_off: 0,
            insns_size: insns.len() as u32,
            insns,
        };
        let blocks = build_cfg(&code);
        assert!(!blocks.is_empty());
    }

    #[test]
    fn test_phi_insertion() {
        let mut blocks = HashMap::new();
        blocks.insert(
            0,
            BasicBlock {
                id: 0,
                start_pc: 0,
                end_pc: 1,
                instructions: vec![SsaInstruction::Move {
                    dest: 1,
                    src: SsaOperand::ConstI32(1),
                }],
                successors: vec![2],
                predecessors: vec![],
            },
        );
        blocks.insert(
            2,
            BasicBlock {
                id: 2,
                start_pc: 2,
                end_pc: 3,
                instructions: vec![SsaInstruction::Move {
                    dest: 1,
                    src: SsaOperand::Register(1),
                }],
                successors: vec![],
                predecessors: vec![0, 4],
            },
        );
        blocks.insert(
            4,
            BasicBlock {
                id: 4,
                start_pc: 4,
                end_pc: 5,
                instructions: vec![SsaInstruction::Nop],
                successors: vec![2],
                predecessors: vec![],
            },
        );
        insert_phi_nodes(&mut blocks);
        let merge = blocks.get(&2).unwrap();
        assert!(merge.instructions.iter().any(|i| matches!(i, SsaInstruction::Phi { .. })));
    }
}
