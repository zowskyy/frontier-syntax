// FRONTIER SYNTAX — PARSER GRAMMAR (Audit Cycle 2)
// ANTLR v4.13.1
// Imports token definitions from syntax/lexicon.ebnf via token_regex_table.json
// Parser emits raw AST only. No name resolution in parser.

grammar Frontier;

@header {
// ANTLR v4.13.1 — Frontier Syntax Parser
// Max nesting depth enforced at parse time: 64
}

program
    : statement* EOF
    ;

statement
    : letDecl
    | fnDecl
    | returnStmt
    | ifStmt
    | block
    | exprStmt
    ;

    letDecl
    : LET IDENTIFIER COLON typeSpec OP_ASSIGN expression SEMICOLON
    ;

fnDecl
    : FN IDENTIFIER LPAREN paramList? RPAREN COLON typeSpec block
    ;

paramList
    : param (COMMA param)*
    ;

param
    : IDENTIFIER COLON typeSpec
    ;

returnStmt
    : RETURN expression? SEMICOLON
    ;

ifStmt
    : IF LPAREN expression RPAREN block (ELSE block)?
    ;

block
    : LBRACE statement* RBRACE
    ;

exprStmt
    : expression SEMICOLON
    ;

// Precedence level 8: Logical OR (left-associative)
expression
    : logicalOr
    ;

logicalOr
    : logicalAnd (OP_LOGICAL_OR logicalAnd)*
    ;

// Precedence level 7: Logical AND (left-associative)
logicalAnd
    : equality (OP_LOGICAL_AND equality)*
    ;

// Precedence level 6: Equality (left-associative)
equality
    : relational ((OP_EQUAL | OP_NOT_EQUAL) relational)*
    ;

// Precedence level 5: Relational (left-associative)
relational
    : additive ((OP_LESS | OP_GREATER | OP_LESS_EQUAL | OP_GREATER_EQUAL) additive)*
    ;

// Precedence level 4: Additive (left-associative)
additive
    : exponent ((OP_PLUS | OP_MINUS) exponent)*
    ;

// Exponentiation: right-associative (exception to left-assoc rule)
exponent
    : multiplicative (OP_EXPONENT exponent)?
    ;

// Precedence level 3: Multiplicative (left-associative)
multiplicative
    : unary ((OP_MULTIPLY | OP_DIVIDE | OP_MODULO) unary)*
    ;

// Precedence level 2: Unary (right-associative)
unary
    : (OP_MINUS | OP_BANG | OP_TILDE) unary
    | postfix
    ;

// Precedence level 1: Primary + postfix (function call, field access, required annot)
postfix
    : primary (LPAREN argList? RPAREN | DOT IDENTIFIER | OP_BANG)*
    ;

primary
    : INTEGER_LITERAL
    | FLOAT_LITERAL
    | STRING_LITERAL
    | KW_TRUE
    | KW_FALSE
    | KW_NULL
    | IDENTIFIER
    | LPAREN expression RPAREN
    ;

argList
    : expression (COMMA expression)*
    ;

typeSpec
    : baseType (OP_OPTIONAL | OP_BANG)?
    ;

baseType
    : KW_INT
    | KW_FLOAT
    | KW_BOOL
    | KW_STRING
    | KW_VOID
    | IDENTIFIER
    ;

// --- Lexer rules (mirror syntax/token_regex_table.json) ---

LET     : 'let' ;
FN      : 'fn' ;
RETURN  : 'return' ;
IF      : 'if' ;
ELSE    : 'else' ;
KW_TRUE  : 'true' ;
KW_FALSE : 'false' ;
KW_NULL  : 'null' ;
KW_INT   : 'int' ;
KW_FLOAT : 'float' ;
KW_BOOL  : 'bool' ;
KW_STRING: 'string' ;
KW_VOID  : 'void' ;

OP_EXPONENT     : '^' ;
OP_LOGICAL_OR   : '||' ;
OP_LOGICAL_AND  : '&&' ;
OP_EQUAL        : '==' ;
OP_NOT_EQUAL    : '!=' ;
OP_LESS_EQUAL   : '<=' ;
OP_GREATER_EQUAL: '>=' ;
OP_LESS         : '<' ;
OP_GREATER      : '>' ;
OP_PLUS         : '+' ;
OP_MINUS        : '-' ;
OP_MULTIPLY     : '*' ;
OP_DIVIDE       : '/' ;
OP_MODULO       : '%' ;
OP_BANG         : '!' ;
OP_TILDE        : '~' ;
OP_ASSIGN       : '=' ;
OP_OPTIONAL     : '?' ;

LPAREN    : '(' ;
RPAREN    : ')' ;
LBRACE    : '{' ;
RBRACE    : '}' ;
COMMA     : ',' ;
SEMICOLON : ';' ;
COLON     : ':' ;
DOT       : '.' ;

INTEGER_LITERAL
    : '0' | [1-9] [0-9]*
    ;

FLOAT_LITERAL
    : INTEGER_LITERAL '.' [0-9]+ ([eE] [+-]? [0-9]+)?
    | INTEGER_LITERAL [eE] [+-]? [0-9]+
    ;

STRING_LITERAL
    : '"' (~["\\\r\n] | '\\' [ntr"\\])* '"'
    ;

IDENTIFIER
    : [A-Za-z_] [A-Za-z0-9_]*
    ;

LINE_COMMENT
    : '//' ~[\r\n]* '\n' -> skip
    ;

BLOCK_COMMENT
    : '/*' .*? '*/' -> skip
    ;

WS
    : [ \t\r\n]+ -> skip
    ;
