// Frontier Syntax Lexer — re2c v3.1
// Generated from syntax/token_regex_table.json
// Input MUST be NFC-normalized UTF-8 before calling frontier_lex()

#include <stddef.h>
#include <string.h>

typedef enum {
    TOK_EOF = 0,
    TOK_KW_LET, TOK_KW_FN, TOK_KW_RETURN, TOK_KW_IF, TOK_KW_ELSE,
    TOK_KW_TRUE, TOK_KW_FALSE, TOK_KW_NULL,
    TOK_KW_INT, TOK_KW_FLOAT, TOK_KW_BOOL, TOK_KW_STRING, TOK_KW_VOID,
    TOK_IDENTIFIER,
    TOK_INTEGER_LITERAL, TOK_FLOAT_LITERAL, TOK_STRING_LITERAL,
    TOK_OP_EXPONENT, TOK_OP_LOGICAL_OR, TOK_OP_LOGICAL_AND,
    TOK_OP_EQUAL, TOK_OP_NOT_EQUAL, TOK_OP_LESS_EQUAL, TOK_OP_GREATER_EQUAL,
    TOK_OP_LESS, TOK_OP_GREATER,
    TOK_OP_PLUS, TOK_OP_MINUS, TOK_OP_MULTIPLY, TOK_OP_DIVIDE, TOK_OP_MODULO,
    TOK_OP_BANG, TOK_OP_TILDE, TOK_OP_ASSIGN, TOK_OP_OPTIONAL,
    TOK_LPAREN, TOK_RPAREN, TOK_LBRACE, TOK_RBRACE,
    TOK_LBRACKET, TOK_RBRACKET,
    TOK_COMMA, TOK_SEMICOLON, TOK_COLON, TOK_DOT,
    TOK_ERROR
} frontier_token_type_t;

typedef struct {
    frontier_token_type_t type;
    const char *start;
    size_t length;
    unsigned line;
    unsigned column;
} frontier_token_t;

static int frontier_lex_one(const char **cursor, const char *limit,
                            frontier_token_t *out, unsigned *line, unsigned *col) {
    const char *token_start;

    if (*cursor >= limit) {
        out->type = TOK_EOF;
        out->start = *cursor;
        out->length = 0;
        out->line = *line;
        out->column = *col;
        return 1;
    }

    for (;;) {
        token_start = *cursor;

/*!re2c
        re2c:yyfill:enable = 0;

        letter = [A-Za-z_];
        digit = [0-9];
        idcont = letter | digit;
        identifier = letter idcont*;
        integer = "0" | [1-9] digit*;
        float_lit = integer "." digit+ ([eE] [+-]? digit+)? | integer [eE] [+-]? digit+;
        string_char = [^"\\\n\r] | "\\" [ntr"\\];
        string_lit = "\"" string_char* "\"";

        * {
            "let" / idcont { out->type = TOK_KW_LET; goto token_done; }
            "fn" / idcont { out->type = TOK_KW_FN; goto token_done; }
            "return" / idcont { out->type = TOK_KW_RETURN; goto token_done; }
            "if" / idcont { out->type = TOK_KW_IF; goto token_done; }
            "else" / idcont { out->type = TOK_KW_ELSE; goto token_done; }
            "true" / idcont { out->type = TOK_KW_TRUE; goto token_done; }
            "false" / idcont { out->type = TOK_KW_FALSE; goto token_done; }
            "null" / idcont { out->type = TOK_KW_NULL; goto token_done; }
            "int" / idcont { out->type = TOK_KW_INT; goto token_done; }
            "float" / idcont { out->type = TOK_KW_FLOAT; goto token_done; }
            "bool" / idcont { out->type = TOK_KW_BOOL; goto token_done; }
            "string" / idcont { out->type = TOK_KW_STRING; goto token_done; }
            "void" / idcont { out->type = TOK_KW_VOID; goto token_done; }

            "||" { out->type = TOK_OP_LOGICAL_OR; goto token_done; }
            "&&" { out->type = TOK_OP_LOGICAL_AND; goto token_done; }
            "==" { out->type = TOK_OP_EQUAL; goto token_done; }
            "!=" { out->type = TOK_OP_NOT_EQUAL; goto token_done; }
            "<=" { out->type = TOK_OP_LESS_EQUAL; goto token_done; }
            ">=" { out->type = TOK_OP_GREATER_EQUAL; goto token_done; }
            "^"  { out->type = TOK_OP_EXPONENT; goto token_done; }
            "<"  { out->type = TOK_OP_LESS; goto token_done; }
            ">"  { out->type = TOK_OP_GREATER; goto token_done; }
            "+"  { out->type = TOK_OP_PLUS; goto token_done; }
            "-"  { out->type = TOK_OP_MINUS; goto token_done; }
            "*"  { out->type = TOK_OP_MULTIPLY; goto token_done; }
            "/"  { out->type = TOK_OP_DIVIDE; goto token_done; }
            "%"  { out->type = TOK_OP_MODULO; goto token_done; }
            "!"  { out->type = TOK_OP_BANG; goto token_done; }
            "~"  { out->type = TOK_OP_TILDE; goto token_done; }
            "="  { out->type = TOK_OP_ASSIGN; goto token_done; }
            "?"  { out->type = TOK_OP_OPTIONAL; goto token_done; }

            "(" { out->type = TOK_LPAREN; goto token_done; }
            ")" { out->type = TOK_RPAREN; goto token_done; }
            "{" { out->type = TOK_LBRACE; goto token_done; }
            "}" { out->type = TOK_RBRACE; goto token_done; }
            "[" { out->type = TOK_LBRACKET; goto token_done; }
            "]" { out->type = TOK_RBRACKET; goto token_done; }
            "," { out->type = TOK_COMMA; goto token_done; }
            ";" { out->type = TOK_SEMICOLON; goto token_done; }
            ":" { out->type = TOK_COLON; goto token_done; }
            "." { out->type = TOK_DOT; goto token_done; }

            [ \t\r\n]+ { continue; }
            "//" [^\n]* "\n" { continue; }
            "/*" ([^*] | "*" [^/])* "*/" { continue; }

            float_lit { out->type = TOK_FLOAT_LITERAL; goto token_done; }
            integer { out->type = TOK_INTEGER_LITERAL; goto token_done; }
            string_lit { out->type = TOK_STRING_LITERAL; goto token_done; }
            identifier { out->type = TOK_IDENTIFIER; goto token_done; }

            * { out->type = TOK_ERROR; goto token_done; }
        }
*/

token_done:
        out->start = token_start;
        out->length = (size_t)(*cursor - token_start);
        out->line = *line;
        out->column = *col;

        for (const char *p = token_start; p < *cursor; p++) {
            if (*p == '\n') {
                (*line)++;
                *col = 1;
            } else {
                (*col)++;
            }
        }
        return 1;
    }
}
