/*
 ==============================================================================
 
 PyJUCEParameter.h
 Created: 6 Jul 2016 10:36:47am
 Author:  martin hermant
 
 ==============================================================================
 */

#ifndef PYJUCEPARAMETER_H_INCLUDED
#define PYJUCEPARAMETER_H_INCLUDED
#include "JuceHeader.h"
#include "PythonUtils.h"
class PyJUCEAPI;

class PyJUCEParameter{
public:
	
  PyJUCEParameter(PyObject * o,const String & _name);
  virtual ~PyJUCEParameter();


  String name;
  var value;
  Rectangle<float> relativeArea;
  NamedValueSet  properties;

  virtual void setValue(var v);
  virtual var getValue();



  Component * buildComponent();

	
protected:
	// need to be overriden
	virtual Component * createComponent(var v,const NamedValueSet & properties)=0;
	virtual PyObject* getPythonObject()=0;
  virtual void updateComponentState(Component * c){};
  virtual   void registerListener(Component *c){};
  virtual void removeListener(Component *c){};

  void updateFromPython();

	
  friend class PyJUCEAPI;
  friend class PyJUCEParameterBuilder;
	PyObject* cbFunc;
  PyObject* pyRef;
  PyObject * pyVal;


  PyObject* listenerName;
	PyJUCEAPI * pyJuceApi;


  void deleteOldComponents();
  Array<WeakReference<Component> > linkedComponents;

private:
  void linkToJuceApi(PyJUCEAPI * );
  void setPythonCallback(PyObject *);

	
};

class PyJUCEParameterBuilder{
public:
	PyJUCEParameterBuilder(PyJUCEAPI* _py):pyAPI(_py){}
	static PyJUCEParameter * buildParamFromObject( PyObject* );

	PyJUCEAPI * pyAPI;
};

class PyFloatParameter;

#endif  // PYJUCEPARAMETER_H_INCLUDED
