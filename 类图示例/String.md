classDiagram
direction BT
class AbstractStringBuilder
class CharSequence {
<<Interface>>

}
class Comparable~T~ {
<<Interface>>

}
class Constable {
<<Interface>>

}
class ConstantDesc {
<<Interface>>

}
class Serializable {
<<Interface>>

}
class String
class StringBuffer
class StringBuilder

AbstractStringBuilder  ..>  CharSequence 
String  ..>  CharSequence 
String  ..>  Comparable~T~ 
String  ..>  Constable 
String  ..>  ConstantDesc 
String  ..>  Serializable 
StringBuffer  -->  AbstractStringBuilder 
StringBuffer  ..>  CharSequence 
StringBuffer  ..>  Comparable~T~ 
StringBuffer  ..>  Serializable 
StringBuilder  -->  AbstractStringBuilder 
StringBuilder  ..>  CharSequence 
StringBuilder  ..>  Comparable~T~ 
StringBuilder  ..>  Serializable 
