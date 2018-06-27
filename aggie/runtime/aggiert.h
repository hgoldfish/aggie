#ifndef AGGIERT_H
#define AGGIERT_H

#include <QList>

#include "aggie.h"

#define aggie_dirty
typedef void* aggie_memory;
typedef void* aggie_machine;


class AggieType {
public:
    AggieType(const QString &name, uint64_t size)
        :name(name), size(size){
    }
    AggieType(const AggieType& other)
        :name(other.name), size(other.size){
    }
public:
    const QString &getName() const {
        return name;
    }
    int64_t getSize() const {
        return size;
    }
    void setSize(int64_t size) {
        this->size = size;
    }
private:
    QString name;
    int64_t size;
};

class AggieMachine {
public:
    void addType(const AggieType &type) {types.append(type);}
private:
    QList<AggieType> types;
};

#endif
