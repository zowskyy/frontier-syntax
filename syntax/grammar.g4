// Frontier Syntax — ANTLR v4.13.1 Grammar (Audit Cycle 2)
// Extends Cycle 1 lexicon with module system, types, and FFI surface syntax.
// Consumed by: frontier-parser crate + Lighthouse browser validation (future WASM).

grammar Frontier;

program
    : moduleDecl importDecl* (typeDecl | externDecl | functionDecl)* EOF
    ;

moduleDecl
    : 'module' IDENTIFIER ';'
    ;

importDecl
    : 'import' qualifiedName '{' importItem (',' importItem)* '}' ';'
    | 'import' qualifiedName ';'
    ;

importItem
    : IDENTIFIER
    ;

typeDecl
    : 'type' IDENTIFIER '=' typeExpr ';'
    ;

externDecl
    : 'extern' 'fn' IDENTIFIER '(' paramList? ')' '->' typeExpr ';'
    ;

functionDecl
    : 'fn' IDENTIFIER '(' paramList? ')' '->' typeExpr block
    ;

paramList
    : param (',' param)*
    ;

param
    : IDENTIFIER ':' typeExpr
    ;

block
    : '{' statement* '}'
    ;

statement
    : 'let' IDENTIFIER '=' expression ';'
    | 'let' '_' '=' expression ';'
    | expression ';'
    | 'return' expression? ';'
    | 'for' IDENTIFIER 'in' expression block
    ;

expression
    : expression '?'                                          # trySuffix
    | expression '.' IDENTIFIER '(' argumentList? ')'           # methodCall
    | expression '::' IDENTIFIER '(' argumentList? ')'          # associatedCall
    | IDENTIFIER '::' IDENTIFIER '(' argumentList? ')'          # staticCall
    | 'Ok' '(' expression ')'                                   # okCtor
    | 'Err' '(' expression ')'                                  # errCtor
    | IDENTIFIER '(' argumentList? ')'                          # call
    | expression '[' expression ']'                           # index
    | expression '.' IDENTIFIER                                 # fieldAccess
    | '(' expression ')'
    | literal
    | IDENTIFIER
    | arrayLiteral
    | structLiteral
    ;

argumentList
    : expression (',' expression)*
    ;

arrayLiteral
    : '[' (expression (',' expression)*)? ']'
    ;

structLiteral
    : '{' structField (',' structField)* '}'
    ;

structField
    : IDENTIFIER ':' typeExpr
    | '(' STRING_LITERAL ',' STRING_LITERAL ')'
    ;

typeExpr
    : 'opaque'
    | 'void'
    | 'int' | 'float' | 'bool' | 'string'
    | 'Int' | 'Float' | 'Bool' | 'String' | 'Binary' | 'Void'
    | 'Result' '<' typeExpr ',' typeExpr '>'
    | 'Vec' '<' typeExpr '>'
    | 'Option' '<' typeExpr '>'
    | '(' typeExpr ',' typeExpr ')'
    | '&' typeExpr
    | IDENTIFIER
    ;

literal
    : INTEGER_LITERAL
    | FLOAT_LITERAL
    | STRING_LITERAL
    | 'true' | 'false' | 'null'
    ;

qualifiedName
    : IDENTIFIER ('.' IDENTIFIER)*
    ;

// Lexer rules — Cycle 1 + Cycle 2 (see syntax/token_regex_table.json + cycle2/extensions.json)

IDENTIFIER      : [A-Za-z_][A-Za-z0-9_]* ;
INTEGER_LITERAL : '0' | [1-9][0-9]* ;
FLOAT_LITERAL   : INTEGER_LITERAL '.' [0-9]+ ([eE] [+-]? INTEGER_LITERAL)?
                | INTEGER_LITERAL [eE] [+-]? INTEGER_LITERAL
                ;
STRING_LITERAL  : '"' (~["\\\r\n] | '\\' [ntr"\\])* '"' ;

LINE_COMMENT    : '//' ~[\r\n]* -> skip ;
BLOCK_COMMENT   : '/*' .*? '*/' -> skip ;
WS              : [ \t\r\n]+ -> skip ;
