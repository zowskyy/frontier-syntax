use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum DexError {
    #[error("invalid DEX magic: expected dex\\n035\\0")]
    InvalidMagic,
    #[error("truncated DEX at offset {0}")]
    Truncated(usize),
    #[error("unsupported DEX version")]
    UnsupportedVersion,
    #[error("parse error: {0}")]
    Parse(String),
}

pub type Result<T> = std::result::Result<T, DexError>;

/// Android DEX header (112 bytes).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DexHeader {
    pub magic: [u8; 8],
    pub checksum: u32,
    pub signature: [u8; 20],
    pub file_size: u32,
    pub header_size: u32,
    pub endian_tag: u32,
    pub link_size: u32,
    pub link_off: u32,
    pub map_off: u32,
    pub string_ids_size: u32,
    pub string_ids_off: u32,
    pub type_ids_size: u32,
    pub type_ids_off: u32,
    pub proto_ids_size: u32,
    pub proto_ids_off: u32,
    pub field_ids_size: u32,
    pub field_ids_off: u32,
    pub method_ids_size: u32,
    pub method_ids_off: u32,
    pub class_defs_size: u32,
    pub class_defs_off: u32,
    pub data_size: u32,
    pub data_off: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u16)]
pub enum MapItemType {
    HeaderItem = 0x0000,
    StringIdItem = 0x0001,
    TypeIdItem = 0x0002,
    ProtoIdItem = 0x0003,
    FieldIdItem = 0x0004,
    MethodIdItem = 0x0005,
    ClassDefItem = 0x0006,
    CallSiteIdItem = 0x0007,
    MethodHandleItem = 0x0008,
    MapList = 0x1000,
    TypeList = 0x1001,
    AnnotationSetRefList = 0x1002,
    AnnotationSetItem = 0x1003,
    ClassDataItem = 0x2000,
    CodeItem = 0x2001,
    StringDataItem = 0x2002,
    DebugInfoItem = 0x2003,
    AnnotationItem = 0x2004,
    EncodedArrayItem = 0x2005,
    AnnotationsDirectoryItem = 0x2006,
    Unknown = 0xFFFF,
}

impl MapItemType {
    pub fn from_u16(v: u16) -> Self {
        match v {
            0x0000 => Self::HeaderItem,
            0x0001 => Self::StringIdItem,
            0x0002 => Self::TypeIdItem,
            0x0003 => Self::ProtoIdItem,
            0x0004 => Self::FieldIdItem,
            0x0005 => Self::MethodIdItem,
            0x0006 => Self::ClassDefItem,
            0x0007 => Self::CallSiteIdItem,
            0x0008 => Self::MethodHandleItem,
            0x1000 => Self::MapList,
            0x1001 => Self::TypeList,
            0x2000 => Self::ClassDataItem,
            0x2001 => Self::CodeItem,
            0x2002 => Self::StringDataItem,
            _ => Self::Unknown,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapItem {
    pub kind: MapItemType,
    pub size: u32,
    pub offset: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StringId {
    pub offset: u32,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TypeId {
    pub descriptor_idx: u32,
    pub descriptor: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProtoId {
    pub shorty_idx: u32,
    pub return_type_idx: u32,
    pub parameters_off: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FieldId {
    pub class_idx: u16,
    pub type_idx: u16,
    pub name_idx: u32,
    pub name: String,
    pub type_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MethodId {
    pub class_idx: u16,
    pub proto_idx: u16,
    pub name_idx: u32,
    pub name: String,
    pub class_name: String,
    pub return_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassDef {
    pub class_idx: u32,
    pub access_flags: u32,
    pub superclass_idx: u32,
    pub interfaces_off: u32,
    pub source_file_idx: u32,
    pub annotations_off: u32,
    pub class_data_off: u32,
    pub static_values_off: u32,
    pub class_name: String,
    pub methods: Vec<ClassMethod>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassMethod {
    pub method_idx: u32,
    pub access_flags: u32,
    pub code_off: u32,
    pub name: String,
    pub code: Option<CodeItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeItem {
    pub registers_size: u16,
    pub ins_size: u16,
    pub outs_size: u16,
    pub tries_size: u16,
    pub debug_info_off: u32,
    pub insns_size: u32,
    pub insns: Vec<u16>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeKind {
    Root,
    Class,
    Method,
    Phi,
    If,
    Loop,
    Switch,
    Block,
    Instruction,
}

impl NodeKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Root => "ROOT",
            Self::Class => "CLASS",
            Self::Method => "METHOD",
            Self::Phi => "PHI",
            Self::If => "IF",
            Self::Loop => "LOOP",
            Self::Switch => "SWITCH",
            Self::Block => "BLOCK",
            Self::Instruction => "INSTRUCTION",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HybridNode {
    pub id: u32,
    pub kind: NodeKind,
    pub ir_data: Vec<u8>,
    pub ast_parent: Option<u32>,
    pub ast_children: Vec<u32>,
    pub label: String,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HybridGraph {
    pub nodes: HashMap<u32, HybridNode>,
    next_id: u32,
    pub root_id: Option<u32>,
}

impl HybridGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_node(&mut self, kind: NodeKind, label: impl Into<String>, ir_data: Vec<u8>) -> u32 {
        let id = self.next_id;
        self.next_id += 1;
        self.nodes.insert(
            id,
            HybridNode {
                id,
                kind,
                ir_data,
                ast_parent: None,
                ast_children: Vec::new(),
                label: label.into(),
            },
        );
        id
    }

    pub fn link(&mut self, parent: u32, child: u32) {
        if let Some(p) = self.nodes.get_mut(&parent) {
            if !p.ast_children.contains(&child) {
                p.ast_children.push(child);
            }
        }
        if let Some(c) = self.nodes.get_mut(&child) {
            c.ast_parent = Some(parent);
        }
    }

    pub fn get(&self, id: u32) -> Option<&HybridNode> {
        self.nodes.get(&id)
    }

    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DexFile {
    pub header: DexHeader,
    pub map_items: Vec<MapItem>,
    pub strings: Vec<StringId>,
    pub types: Vec<TypeId>,
    pub protos: Vec<ProtoId>,
    pub fields: Vec<FieldId>,
    pub methods: Vec<MethodId>,
    pub classes: Vec<ClassDef>,
    pub graph: HybridGraph,
}

struct Reader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    fn remaining(&self) -> usize {
        self.data.len().saturating_sub(self.pos)
    }

    fn read_u8(&mut self) -> Result<u8> {
        if self.pos >= self.data.len() {
            return Err(DexError::Truncated(self.pos));
        }
        let v = self.data[self.pos];
        self.pos += 1;
        Ok(v)
    }

    fn read_u16(&mut self) -> Result<u16> {
        if self.pos + 2 > self.data.len() {
            return Err(DexError::Truncated(self.pos));
        }
        let v = u16::from_le_bytes([self.data[self.pos], self.data[self.pos + 1]]);
        self.pos += 2;
        Ok(v)
    }

    fn read_u32(&mut self) -> Result<u32> {
        if self.pos + 4 > self.data.len() {
            return Err(DexError::Truncated(self.pos));
        }
        let v = u32::from_le_bytes([
            self.data[self.pos],
            self.data[self.pos + 1],
            self.data[self.pos + 2],
            self.data[self.pos + 3],
        ]);
        self.pos += 4;
        Ok(v)
    }

    fn read_bytes(&mut self, n: usize) -> Result<Vec<u8>> {
        if self.pos + n > self.data.len() {
            return Err(DexError::Truncated(self.pos));
        }
        let slice = &self.data[self.pos..self.pos + n];
        self.pos += n;
        Ok(slice.to_vec())
    }

    fn seek(&mut self, offset: usize) -> Result<()> {
        if offset > self.data.len() {
            return Err(DexError::Truncated(offset));
        }
        self.pos = offset;
        Ok(())
    }

    fn position(&self) -> usize {
        self.pos
    }
}

fn read_uleb128(r: &mut Reader<'_>) -> Result<u32> {
    let mut result = 0u32;
    let mut shift = 0;
    loop {
        let byte = r.read_u8()? as u32;
        result |= (byte & 0x7f) << shift;
        if byte & 0x80 == 0 {
            break;
        }
        shift += 7;
        if shift > 35 {
            return Err(DexError::Parse("uleb128 overflow".into()));
        }
    }
    Ok(result)
}

fn read_string_data(data: &[u8], offset: usize) -> Result<String> {
    let mut r = Reader::new(data);
    r.seek(offset)?;
    let _utf16_size = read_uleb128(&mut r)?;
    let mut bytes = Vec::new();
    while r.remaining() > 0 {
        let b = r.read_u8()?;
        if b == 0 {
            break;
        }
        bytes.push(b);
    }
    String::from_utf8(bytes).map_err(|e| DexError::Parse(e.to_string()))
}

pub fn parse_dex(bytes: &[u8]) -> Result<DexFile> {
    if bytes.len() < 112 {
        return Err(DexError::Truncated(bytes.len()));
    }
    let mut r = Reader::new(bytes);
    let magic = {
        let m = r.read_bytes(8)?;
        let mut arr = [0u8; 8];
        arr.copy_from_slice(&m);
        arr
    };
    if &magic[0..3] != b"dex" {
        return Err(DexError::InvalidMagic);
    }

    let header = DexHeader {
        magic,
        checksum: r.read_u32()?,
        signature: {
            let s = r.read_bytes(20)?;
            let mut arr = [0u8; 20];
            arr.copy_from_slice(&s);
            arr
        },
        file_size: r.read_u32()?,
        header_size: r.read_u32()?,
        endian_tag: r.read_u32()?,
        link_size: r.read_u32()?,
        link_off: r.read_u32()?,
        map_off: r.read_u32()?,
        string_ids_size: r.read_u32()?,
        string_ids_off: r.read_u32()?,
        type_ids_size: r.read_u32()?,
        type_ids_off: r.read_u32()?,
        proto_ids_size: r.read_u32()?,
        proto_ids_off: r.read_u32()?,
        field_ids_size: r.read_u32()?,
        field_ids_off: r.read_u32()?,
        method_ids_size: r.read_u32()?,
        method_ids_off: r.read_u32()?,
        class_defs_size: r.read_u32()?,
        class_defs_off: r.read_u32()?,
        data_size: r.read_u32()?,
        data_off: r.read_u32()?,
    };

    if header.endian_tag != 0x1234_5678 {
        return Err(DexError::UnsupportedVersion);
    }

    let map_items = parse_map_list(bytes, header.map_off as usize)?;
    let strings = parse_string_ids(bytes, &header)?;
    let types = parse_type_ids(bytes, &header, &strings)?;
    let protos = parse_proto_ids(bytes, &header)?;
    let fields = parse_field_ids(bytes, &header, &strings, &types)?;
    let methods = parse_method_ids(bytes, &header, &strings, &types, &protos)?;
    let classes = parse_class_defs(bytes, &header, &strings, &types, &methods)?;

    let mut graph = HybridGraph::new();
    let root_id = graph.add_node(NodeKind::Root, "dex_root", header.magic.to_vec());
    graph.root_id = Some(root_id);

    for item in &map_items {
        let label = format!("{:?}@{}", item.kind, item.offset);
        let node = graph.add_node(
            NodeKind::Block,
            label,
            item.offset.to_le_bytes().to_vec(),
        );
        graph.link(root_id, node);
    }

    for class in &classes {
        let class_node = graph.add_node(
            NodeKind::Class,
            &class.class_name,
            class.access_flags.to_le_bytes().to_vec(),
        );
        graph.link(root_id, class_node);
        for method in &class.methods {
            let method_node = graph.add_node(
                NodeKind::Method,
                format!("{}::{}", class.class_name, method.name),
                method.access_flags.to_le_bytes().to_vec(),
            );
            graph.link(class_node, method_node);
        }
    }

    Ok(DexFile {
        header,
        map_items,
        strings,
        types,
        protos,
        fields,
        methods,
        classes,
        graph,
    })
}

fn parse_map_list(bytes: &[u8], offset: usize) -> Result<Vec<MapItem>> {
    if offset == 0 {
        return Ok(Vec::new());
    }
    let mut r = Reader::new(bytes);
    r.seek(offset)?;
    let size = r.read_u32()?;
    let mut items = Vec::with_capacity(size as usize);
    for _ in 0..size {
        let kind = MapItemType::from_u16(r.read_u16()?);
        r.read_u16()?; // unused
        let count = r.read_u32()?;
        let off = r.read_u32()?;
        items.push(MapItem {
            kind,
            size: count,
            offset: off,
        });
    }
    Ok(items)
}

fn parse_string_ids(bytes: &[u8], header: &DexHeader) -> Result<Vec<StringId>> {
    let mut ids = Vec::with_capacity(header.string_ids_size as usize);
    for i in 0..header.string_ids_size {
        let mut r = Reader::new(bytes);
        let off = header.string_ids_off as usize + (i as usize) * 4;
        r.seek(off)?;
        let str_off = r.read_u32()? as usize;
        let value = read_string_data(bytes, str_off)?;
        ids.push(StringId {
            offset: str_off as u32,
            value,
        });
    }
    Ok(ids)
}

fn parse_type_ids(bytes: &[u8], header: &DexHeader, strings: &[StringId]) -> Result<Vec<TypeId>> {
    let mut types = Vec::with_capacity(header.type_ids_size as usize);
    for i in 0..header.type_ids_size {
        let mut r = Reader::new(bytes);
        r.seek(header.type_ids_off as usize + (i as usize) * 4)?;
        let descriptor_idx = r.read_u32()?;
        let descriptor = strings
            .get(descriptor_idx as usize)
            .map(|s| s.value.clone())
            .unwrap_or_else(|| "Ljava/lang/Object;".into());
        types.push(TypeId {
            descriptor_idx,
            descriptor,
        });
    }
    Ok(types)
}

fn parse_proto_ids(bytes: &[u8], header: &DexHeader) -> Result<Vec<ProtoId>> {
    let mut protos = Vec::with_capacity(header.proto_ids_size as usize);
    for i in 0..header.proto_ids_size {
        let mut r = Reader::new(bytes);
        r.seek(header.proto_ids_off as usize + (i as usize) * 12)?;
        protos.push(ProtoId {
            shorty_idx: r.read_u32()?,
            return_type_idx: r.read_u32()?,
            parameters_off: r.read_u32()?,
        });
    }
    Ok(protos)
}

fn parse_field_ids(
    bytes: &[u8],
    header: &DexHeader,
    strings: &[StringId],
    types: &[TypeId],
) -> Result<Vec<FieldId>> {
    let mut fields = Vec::with_capacity(header.field_ids_size as usize);
    for i in 0..header.field_ids_size {
        let mut r = Reader::new(bytes);
        r.seek(header.field_ids_off as usize + (i as usize) * 8)?;
        let class_idx = r.read_u16()?;
        let type_idx = r.read_u16()?;
        let name_idx = r.read_u32()?;
        let name = strings
            .get(name_idx as usize)
            .map(|s| s.value.clone())
            .unwrap_or_default();
        let type_name = types
            .get(type_idx as usize)
            .map(|t| t.descriptor.clone())
            .unwrap_or_default();
        fields.push(FieldId {
            class_idx,
            type_idx,
            name_idx,
            name,
            type_name,
        });
    }
    Ok(fields)
}

fn parse_method_ids(
    bytes: &[u8],
    header: &DexHeader,
    strings: &[StringId],
    types: &[TypeId],
    protos: &[ProtoId],
) -> Result<Vec<MethodId>> {
    let mut methods = Vec::with_capacity(header.method_ids_size as usize);
    for i in 0..header.method_ids_size {
        let mut r = Reader::new(bytes);
        r.seek(header.method_ids_off as usize + (i as usize) * 8)?;
        let class_idx = r.read_u16()?;
        let proto_idx = r.read_u16()?;
        let name_idx = r.read_u32()?;
        let name = strings
            .get(name_idx as usize)
            .map(|s| s.value.clone())
            .unwrap_or_default();
        let class_name = types
            .get(class_idx as usize)
            .map(|t| t.descriptor.clone())
            .unwrap_or_default();
        let return_type = protos
            .get(proto_idx as usize)
            .and_then(|p| types.get(p.return_type_idx as usize))
            .map(|t| t.descriptor.clone())
            .unwrap_or_else(|| "V".into());
        methods.push(MethodId {
            class_idx,
            proto_idx,
            name_idx,
            name,
            class_name,
            return_type,
        });
    }
    Ok(methods)
}

fn parse_class_defs(
    bytes: &[u8],
    header: &DexHeader,
    _strings: &[StringId],
    types: &[TypeId],
    methods: &[MethodId],
) -> Result<Vec<ClassDef>> {
    let mut classes = Vec::with_capacity(header.class_defs_size as usize);
    for i in 0..header.class_defs_size {
        let mut r = Reader::new(bytes);
        r.seek(header.class_defs_off as usize + (i as usize) * 32)?;
        let class_idx = r.read_u32()?;
        let access_flags = r.read_u32()?;
        let superclass_idx = r.read_u32()?;
        let interfaces_off = r.read_u32()?;
        let source_file_idx = r.read_u32()?;
        let annotations_off = r.read_u32()?;
        let class_data_off = r.read_u32()?;
        let static_values_off = r.read_u32()?;
        let class_name = types
            .get(class_idx as usize)
            .map(|t| t.descriptor.clone())
            .unwrap_or_default();

        let class_methods = if class_data_off != 0 {
            parse_class_data(bytes, class_data_off as usize, methods)?
        } else {
            Vec::new()
        };

        let _ = (superclass_idx, interfaces_off, source_file_idx, annotations_off, static_values_off);

        classes.push(ClassDef {
            class_idx,
            access_flags,
            superclass_idx,
            interfaces_off,
            source_file_idx,
            annotations_off,
            class_data_off,
            static_values_off,
            class_name,
            methods: class_methods,
        });
    }
    Ok(classes)
}

fn parse_class_data(
    bytes: &[u8],
    offset: usize,
    method_ids: &[MethodId],
) -> Result<Vec<ClassMethod>> {
    let mut r = Reader::new(bytes);
    r.seek(offset)?;
    let _static_fields = read_uleb128(&mut r)?;
    for _ in 0.._static_fields {
        let _ = read_uleb128(&mut r)?;
        let _ = read_uleb128(&mut r)?;
    }
    let instance_fields = read_uleb128(&mut r)?;
    for _ in 0..instance_fields {
        let _ = read_uleb128(&mut r)?;
        let _ = read_uleb128(&mut r)?;
    }
    let direct_methods = read_uleb128(&mut r)?;
    let mut class_methods = Vec::new();
    let mut method_idx_acc = 0u32;
    for _ in 0..direct_methods {
        let delta = read_uleb128(&mut r)?;
        method_idx_acc += delta;
        let access_flags = read_uleb128(&mut r)?;
        let code_off = read_uleb128(&mut r)?;
        let mid = method_ids.get(method_idx_acc as usize);
        let name = mid.map(|m| m.name.clone()).unwrap_or_default();
        let code = if code_off != 0 {
            Some(parse_code_item(bytes, code_off as usize)?)
        } else {
            None
        };
        class_methods.push(ClassMethod {
            method_idx: method_idx_acc,
            access_flags,
            code_off,
            name,
            code,
        });
    }
    let virtual_methods = read_uleb128(&mut r)?;
    for _ in 0..virtual_methods {
        let delta = read_uleb128(&mut r)?;
        method_idx_acc += delta;
        let access_flags = read_uleb128(&mut r)?;
        let code_off = read_uleb128(&mut r)?;
        let mid = method_ids.get(method_idx_acc as usize);
        let name = mid.map(|m| m.name.clone()).unwrap_or_default();
        let code = if code_off != 0 {
            Some(parse_code_item(bytes, code_off as usize)?)
        } else {
            None
        };
        class_methods.push(ClassMethod {
            method_idx: method_idx_acc,
            access_flags,
            code_off,
            name,
            code,
        });
    }
    Ok(class_methods)
}

pub fn parse_code_item(bytes: &[u8], offset: usize) -> Result<CodeItem> {
    let mut r = Reader::new(bytes);
    r.seek(offset)?;
    let registers_size = r.read_u16()?;
    let ins_size = r.read_u16()?;
    let outs_size = r.read_u16()?;
    let tries_size = r.read_u16()?;
    let debug_info_off = r.read_u32()?;
    let insns_size = r.read_u32()?;
    let mut insns = Vec::with_capacity(insns_size as usize);
    for _ in 0..insns_size {
        insns.push(r.read_u16()?);
    }
    let _ = (tries_size, debug_info_off, registers_size, ins_size, outs_size);
    Ok(CodeItem {
        registers_size,
        ins_size,
        outs_size,
        tries_size,
        debug_info_off,
        insns_size,
        insns,
    })
}

pub fn dex_type_to_java(descriptor: &str) -> String {
    if descriptor.starts_with('L') && descriptor.ends_with(';') {
        let inner = &descriptor[1..descriptor.len() - 1];
        return inner.replace('/', ".");
    }
    match descriptor {
        "V" => "void".into(),
        "Z" => "boolean".into(),
        "B" => "byte".into(),
        "S" => "short".into(),
        "C" => "char".into(),
        "I" => "int".into(),
        "J" => "long".into(),
        "F" => "float".into(),
        "D" => "double".into(),
        other => other.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_dex() -> Vec<u8> {
        let mut dex = vec![0u8; 512];
        dex[0..8].copy_from_slice(b"dex\n035\0");
        dex[32] = 0x78; // file_size = 120
        dex[36] = 0x70; // header_size = 112
        dex[40] = 0x78;
        dex[41] = 0x56;
        dex[42] = 0x34;
        dex[43] = 0x12; // endian
        dex[52] = 0x70; // map_off = 112
        dex[112] = 1; // map size = 1
        dex[116] = 0; dex[117] = 0; // HeaderItem
        dex[120] = 1; // count
        dex[124] = 0; // offset 0
        dex
    }

    #[test]
    fn test_parse_header() {
        let dex = parse_dex(&minimal_dex()).expect("parse");
        assert_eq!(&dex.header.magic[0..4], b"dex\n");
        assert!(dex.graph.root_id.is_some());
    }

    #[test]
    fn test_invalid_magic() {
        let mut dex = minimal_dex();
        dex[0] = b'X';
        assert!(parse_dex(&dex).is_err());
    }

    #[test]
    fn test_hybrid_graph_link() {
        let mut g = HybridGraph::new();
        let root = g.add_node(NodeKind::Root, "root", vec![]);
        let child = g.add_node(NodeKind::Class, "LFoo;", vec![]);
        g.link(root, child);
        assert_eq!(g.get(child).unwrap().ast_parent, Some(root));
        assert!(g.get(root).unwrap().ast_children.contains(&child));
    }
}
