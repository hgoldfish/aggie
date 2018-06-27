#include <QString>
#include <QTextCodec>
#include <iostream>

#include "aggiert.h"

extern "C" {

aggie_machine aggie_initialize() {
    return static_cast<aggie_machine>(new AggieMachine);
}

void aggie_finallize(aggie_machine machine) {
    AggieMachine *m = static_cast<AggieMachine*>(machine);
    delete m;
}

aggie_memory aggie_malloc(aggie_int size) {
    return static_cast<void*>(new int8_t[size]);
}

void aggie_free(aggie_memory buf) {
    delete[] static_cast<int8_t*>(buf);
}

void aggie_print(aggie_str s) {
    const QString *qs = static_cast<const QString*>(s);
    std::cout << qs->toUtf8().toStdString();
}

void aggie_str_new(aggie_memory strdata, aggie_int length, aggie_dirty aggie_str buf) {
    QString *qs = new(buf) QString();
    QTextCodec *tc = QTextCodec::codecForName("UTF-16LE");
    *qs = tc->toUnicode(static_cast<char*>(strdata), length);
}

void aggie_str_del(aggie_str s) {
    QString *qs = static_cast<QString*>(s);
    qs->~QString();
}

void aggie_str_copy(aggie_dirty aggie_str dest, aggie_str src) {
    const QString *qs_src = static_cast<QString*>(src);
    new(dest) QString(*qs_src);
}

aggie_int aggie_str_len(aggie_str s) {
    const QString *qs = static_cast<const QString*>(s);
    return qs->size();
}

void aggie_str_concat(aggie_str s1, aggie_str s2, aggie_dirty aggie_str result){
    const QString *qs1 = static_cast<const QString*>(s1);
    const QString *qs2 = static_cast<const QString*>(s2);
    new(result) QString(*qs1 + *qs2);
}

aggie_int aggie_str_toint(aggie_str s, aggie_int base, aggie_bool *ok) {
    const QString *qs = static_cast<const QString*>(s);
    bool bok;
    aggie_int i = qs->toLongLong(&bok, static_cast<int>(base));
    *ok = bok ? 1 : 0;
    return i;
}

aggie_float aggie_str_tofloat(aggie_str s, aggie_bool *ok) {
    const QString *qs = static_cast<const QString*>(s);
    bool bok;
    float f = qs->toFloat(&bok);
    *ok = bok ? 1 : 0;
    return f;
}

aggie_int aggie_str_hash(aggie_str s, aggie_int seed) {
    const QString *qs = static_cast<const QString*>(s);
    return qHash(*qs, static_cast<uint>(seed));
}

aggie_bool aggie_str_startswith(aggie_str s, aggie_str prefix) {
    const QString *qs = static_cast<const QString*>(s);
    const QString *qprefix = static_cast<const QString*>(prefix);
    return qs->startsWith(*qprefix);
}

aggie_bool aggie_str_endswith(aggie_str s, aggie_str postfix) {
    const QString *qs = static_cast<const QString*>(s);
    const QString *qpostfix = static_cast<const QString*>(postfix);
    return qs->endsWith(*qpostfix);
}

void aggie_str_fromint(aggie_int i, aggie_int base, aggie_dirty aggie_str s) {
    QString *qs = new(s) QString();
    *qs = QString::number(i, base);
}

void aggie_str_fromfloat(aggie_float f, aggie_dirty aggie_str s) {
    QString *qs = new(s) QString();
    *qs = QString::number(f);
}

void aggie_str_duplicate(aggie_str s, aggie_int times, aggie_dirty aggie_str result) {
    const QString *qs = static_cast<const QString*>(s);
    new(result) QString(qs->repeated(times));
}

aggie_int aggie_str_count(aggie_str s, aggie_str sub) {
    const QString *qs = static_cast<const QString*>(s);
    const QString *qsub = static_cast<const QString*>(sub);
    return qs->count(*qsub);
}

} // end extern "c"
