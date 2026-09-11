""" 
Basics Classes for a "geometrical" graph model: 
  - nodes have a position (x,y,z), and some data (taken from a list of properties)
  - elements (links) connect nodes, they contain some data (taken from a list of properties)

An ordering of Elements, Nodes, and Properties is present, but whenever possible,
the "ID" is used to identify them, instead of their index.


Nodes: 
   Node.ID:    unique ID (int) of the node. IDs never change.
   Node.x,y,z: coordinate of the nodes
   Node.data : dictionary of data stored at the node

Elements: 
   Elem.ID:      unique ID (int) of the element. IDs never change.
   Elem.nodeIDs: list of node IDs making up the element
   Elem.nodes  : list of nodes making the element (by reference) # NOTE: this has cross reference!
   Elem.nodeProps   : properties # Nodal properties. NOTE: cannot be transfered to node if two members are connected to same nodes but with different nodal property (e.g. SubDyn/HydroDyn Diameter)
   Elem.data   : dictionary of data stored at the element
   # Optional
   Elem.propset: string referring to the property set in the dictionary of properties
   Elem.propIDs: IDs used for the properties of this element at each node

NodePropertySets: dictionary of NodeProperties
   Node Property: 
      NProp.ID:  unique ID of the node proprety
      NProp.data: dictionary of data
          

ElemPropertySets: dictionary of ElemProperties

"""

import numpy as np
import pandas as pd
import itertools
print('Using Graph from FEM')


# --------------------------------------------------------------------------------}
# --- Node
# --------------------------------------------------------------------------------{
class Node(object):
    def __init__(self, ID, x, y, z=0, **kwargs):
        self.ID = int(ID)
        self.x  = x
        self.y  = y
        self.z  = z
        self.data  = kwargs

    def setData(self, data_dict):
        """ set or add data"""
        for k,v in data_dict.items():
            #if k in self.data.keys():
            #    print('Warning overriding key {} for node {}'.format(k,self.ID))
            self.data[k]=v

    @property
    def point(self):
        return np.array([self.x, self.y, self.z])

    def __repr__(self):
        s='<Node{:4d}> x:{:7.2f} y:{:7.2f} z:{:7.2f} {:}'.format(self.ID, self.x, self.y, self.z, self.data)
        return s

# --------------------------------------------------------------------------------}
# --- Properties  
# --------------------------------------------------------------------------------{
class Property(dict):
    def __init__(self, ID, data=None, **kwargs):
        """ 
        data is a dictionary
        """
        dict.__init__(self)
        self.ID= int(ID)
        self.update(kwargs)
        if data is not None:
            self.update(data)

    @property
    def data(self):
        return {k:v for k,v in self.items() if k!='ID'}

    def __repr__(self):
        s='<Prop{:4d}> {:}'.format(self.ID, self.data)
        return s

class NodeProperty(Property):
    def __init__(self, ID, data=None, **kwargs):
        Property.__init__(self, ID, data, **kwargs)
    def __repr__(self):
        s='<NPrp{:4d}> {:}'.format(self.ID, self.data)
        return s
    
class ElemProperty(Property):
    def __init__(self, ID, data=None, **kwargs):
        Property.__init__(self, ID, data, **kwargs)
    def __repr__(self):
        s='<EPrp{:4d}> {:}'.format(self.ID, self.data)
        return s


# --------------------------------------------------------------------------------}
# --- Elements 
# --------------------------------------------------------------------------------{
class Element(dict):
    def __init__(self, ID, nodeIDs, nodes=None, propset=None, propIDs=None, properties=None, **kwargs):
        """ 

        """
        self.ID      = int(ID)
        if nodeIDs is None:
            if nodes is not None:
                nodeIDs = [n.ID for n in nodes]
            else:
                raise Exception('If `nodeIDs` are not provided, provide `nodes`')
        self.nodeIDs = nodeIDs
        self.propset = propset  # String representing the key in the graph.NodePropertySets dict
        self.propIDs = propIDs
        self.data    = kwargs     # Nodal data
        self.nodes   = nodes      # Typically a trigger based on nodeIDs # NOTE: Uppercase 
        self.nodeProps= properties # Typically a trigger based on propIDs. Otherwise list of dictionaries
        if (self.propIDs is not None) and (self.propset is None):
            raise Exception('`propset` should be provided if `propIDs` are provided')
        if (self.propIDs is not None) and (self.propset is not None) and properties is not None:
            raise Exception('When providing `propset` & `propIDs`, properties should not be provided')
        if nodes is not None:
            if len(nodes)!=len(nodeIDs):
                raise Exception('List of nodes has different length than list of nodeIDs')
            for i, (ID,n) in enumerate(zip(nodeIDs,nodes)):
                if n.ID!=ID:
                    raise Exception('Node ID do not match {}/={} for node index {}'.format(n.ID,ID,i))
        
    @property
    def length(self):
        n1=self.nodes[0]
        n2=self.nodes[1]
        return np.sqrt((n1.x-n2.x)**2+(n1.y-n2.y)**2+(n1.z-n2.z)**2)

    #@property
    #def nodes(self):
    #    if self._nodes is None:
    #        if self.nodeIDs is not None:
    #            self._nodes=[self.getNode(i) for i in elem.nodeIDs]
    #    return self._nodes

    def swapNodes(self):
        self.nodeIDs   = self.nodeIDs[-1::-1]
        self.nodes     = self.nodes  [-1::-1]
        if self.propIDs is not None:
            self.propIDs   = self.propIDs[-1::-1]
        if self.nodeProps is not None:
            self.nodeProps = self.nodeProps[-1::-1]

    def __repr__(self):
        s='<Elem{:4d}> NodeIDs: {} {}'.format(self.ID, self.nodeIDs, self.data)
        if self.propIDs is not None:
            s+=' {'+'propIDs:{} propset:{}'.format(self.propIDs, self.propset)+'}'
        if self.nodes is not None:
            s+=' l={:.2f}'.format(self.length)
        return s

# --------------------------------------------------------------------------------}
# --- Member
# --------------------------------------------------------------------------------{
class Member(dict):
    """ Members are used when a graph is divided, to keep track of parent elements"""
    def __init__(self, ID, elemIDs):
        """ 

        """
        self.ID      = int(ID)
        self.elemIDs = elemIDs

    def nodeIDs(self, graph):
        nodeIDs=[]
        for eID in self.elemIDs:
            E = graph.getElement(eID)
            nodeIDs.append(E.nodeIDs[0])
        nodeIDs.append(E.nodeIDs[1])
        return nodeIDs

    def getNodes(self, graph):
        return [graph.getNode(nID) for nID in self.nodeIDs(graph)]

    def getElements(self, graph):
        return [graph.getElement(eID) for eID in self.elemIDs]

    def __repr__(self):
        s='<Memb{:4d}> ElemIDs{}'.format(self.ID, self.elemIDs)
        return s

# --------------------------------------------------------------------------------}
# --- Mode 
# --------------------------------------------------------------------------------{
class Mode(dict):
    def __init__(self, displ, name, freq=1, group='default', **kwargs):
        """ """
        dict.__init__(self)
        self['name']  = name
        self['freq']  = freq
        self['group'] = group
        self['displ']  = displ  # displacements nNodes x 3 assuming a given sorting of nodes

    def __repr__(self):
        s='<Mode> name:{:4s} freq:{:} '.format(self['name'], self['freq'])
        return s

    def reSort(self,I):
        self['displ']=self['displ'][I,:]


# --------------------------------------------------------------------------------}
# --- Time Series
# --------------------------------------------------------------------------------{
class TimeSeries(dict):
    def __init__(self, time, mat4=None, displ=None, rot=None, name=None, group='default', absolute=False, element=False):
        """ 
        - time: time vector, array of length nT

        n: number of nodes or elements

        - either: 
            mat4:   nT x n x 4 x 4 - Matrix 4 with rotation and displacement
          or:             
            displ:  nT x n x 3    : displacement vectors for all time steps and node/elements
            rot  :  nT x n x 3 x 3: orientation matrix for all time steps and node/elements

        - absolute: if True `displ`, `rot` or `mat4` are absolute positions/rotations
                    if False, they are relative displacements/rotations from reference.
        - element: if True `displ`, `rot` or `mat4` are for elements 
                   if False `displ`, `rot` or `mat4` are for nodes 
        """
        self['name']  = name
        self['group'] = group
        self['displ'] = displ
        self['rot']   = rot
        self['mat4']  = mat4
        self['group'] = group
        self['time']  = time
        self['absolute']  = absolute
        self['perElement']  = element

    @property
    def timeInfo(self):
        """ return a dictionary with time info"""
        from scipy.stats import mode

        TI = dict()
        nt = len(self['time'])
        t_max = np.max(self['time'])
        t_min = np.min(self['time'])
        t_bar = (self['time']-t_min)/(t_max-t_min)
        dt_bar = np.unique(np.around(np.diff(t_bar), int(np.log10(nt))+2))
        if len(dt_bar)<=max(0.01*nt,1):
            # we assume a constant time step is used
            TI['tMin'] = self['time'][0]
            modes = mode(np.diff(self['time']))[0]
            if np.isscalar(modes):
                TI['dt'  ] = modes
            else:
                TI['dt'  ] = modes[0]
            TI['nt'  ] = nt
        else:
            TI['time'] = list(self['time'])
        return TI

    def mat4(self, flat=True):
        if self['mat4'] is None:
            nt, nn, _ = np.shape(self['displ'])
            mat4 = np.zeros((nt, nn, 4, 4))
            mat4[:,:,3,3]   = 1
            mat4[:,:,:3,:3] = self['rot']
            mat4[:,:,3,:3]  = self['displ']
            self['mat4'] = mat4

        if flat==True:
            nt, nn, _, _ = np.shape(self['mat4'])
            mat4 = self['mat4'].reshape((nt,nn,16)).tolist()
        else:
            mat4 = self['mat4'].tolist()
        return mat4

def displ2mat4(displ, flat=True):
    """ 
    displ: displacement field (nt x nn x 3)
    mat4: mat 4 transformation (nt x nn x 4 x 4) or (nt x nn x 16)
    """
    nt, nn, _ = np.shape(displ)
    mat4 = np.zeros((nt, nn, 4, 4))
    mat4[:,:,3,3]   = 1
    mat4[:,:,:3,:3] = np.eye(3)
    mat4[:,:,3,:3]  = displ
    if flat==True:
        mat4 = mat4.reshape((nt,nn,16))
    return mat4


# --------------------------------------------------------------------------------}
# --- Dummy functions to help debugging  
# --------------------------------------------------------------------------------{
def dummyNodesConn(nNodes, name=''):
    if name=='random':
        Nodes = np.random.randint(100, size=(nNodes,3))
    else:
        raise NotImplementedError()
    Conn = np.zeros((nNodes-1, 2))
    for iN in np.arange(nNodes-1):
        Conn[iN] = [iN, iN+1]
    return Nodes, Conn



def dummyModeDisplacements(Nodes, name='', Ampl=1):
    """ Return dummy displacement field, useful for debugging """
    nN    = len(Nodes)
    displ = np.zeros((nN,3))
    if name=='x-rigid-translation':
        displ[:, 0] = Ampl
    elif name=='y-rigid-translation':
        displ[:, 1] = Ampl
    elif name=='z-rigid-translation':
        displ[:, 2] = Ampl
    elif name=='x-rigid-rotation':
        N0=Nodes[0,:]
        for iN in np.arange(nN):
            DP = Nodes[iN,:] - N0
            displ[iN, : ] = 0
            displ[iN, 1 ] = DP[1]*np.cos(Ampl*np.pi/180) - DP[2]*np.sin(Ampl*np.pi/180) - DP[1]
            displ[iN, 2 ] = DP[1]*np.sin(Ampl*np.pi/180) + DP[2]*np.cos(Ampl*np.pi/180) - DP[2]
    else:
        raise NotImplementedError()

    return displ

def dummyTimeSeriesDisplacements(time, Nodes, name='', Ampl=1):
    t0    = time[0]
    T     = time[-1]-t0
    f     = 1/T
    om    = 2*np.pi*f
    nt    = len(time)
    nN    = len(Nodes)
    displ = np.zeros((nt,nN,3))
    rot   = np.zeros((nt,nN,3,3))

    if name[0]=='x':
        iComp=0
    elif name[0]=='y':
        iComp=1
    elif name[2]=='z':
        iComp=2
    # NOTE: for now rotations are not used
    for it, t in enumerate(time):
        for iN in np.arange(nN):
            rot[it, iN, :,: ] =np.eye(3) 
    if name.find('static')>=0:
        pass
    elif name.find('lin')>0:
        for it, t in enumerate(time):
            displ[it, :, iComp] = Ampl*(t-t0)
    elif name.find('sin')>0:
        for it, t in enumerate(time):
            displ[it, :, iComp] = Ampl*np.sin(om*(t-t0))
    elif name.find('x-rot')>=0:
        N0=Nodes[0,:]
        for iN in np.arange(nN):
            DP = Nodes[iN,:] - N0
            displ[:, iN, : ] = 0
            displ[:, iN, 1 ] = DP[1]*np.cos(om*(time-t0)) - DP[2]*np.sin(om*(time-t0))  - DP[1]
            displ[:, iN, 2 ] = DP[1]*np.sin(om*(time-t0)) + DP[2]*np.cos(om*(time-t0))  - DP[2]
    else:
        raise NotImplementedError('name: ', name)
    return displ


# --------------------------------------------------------------------------------}
# --- Connected Object 
# --------------------------------------------------------------------------------{
class ConnectedObject():
    """ 
    Object:
    - Nodes
    - Connectivity
    - ElemProp
    - TimeSeries
    - Modes
    """
    def __init__(self, name='defaultObject', Nodes=None, Connectivity=None, ElemProps=None):
        self.name=name
        self.setNodes(Nodes)
        self.setConnectivity(Connectivity)
        self.setElemProps(ElemProps)
        self.Modes        = dict()
        self.TimeSeries   = dict()

    @property
    def nNodes(self): 
        try:
            return len(self.Nodes)
        except:
            return 0

    @property
    def nElem(self): 
        try:
            return len(self.Connectivity)
        except:
            return 0

    @property
    def nModes(self): 
        return len(self.Modes)

    @property
    def nTS(self): 
        return len(self.TimeSeries)

    def setNodes(self, nodes):
        if nodes is None:
            self.Nodes=None
            return
        # --- Sanity checks
        nodes = np.asarray(nodes)
        assert(nodes.shape[1] == 3)
        # Add
        self.Nodes = nodes

    def setConnectivity(self, connectivity):
        """
        List of list, may not all be of the same size
        [[self.Nodes.index(n)  for n in e.nodes] for e in self.Elements]
        """
        if connectivity is None:
            self.Connectivity=None
            return
        connectivity=np.asarray(connectivity)
        # --- Sanity
        allcon = list(itertools.chain.from_iterable(connectivity))
        if self.Nodes is None:
            raise Exception('Set Nodes before setting connectivity for object {}'.format(self.name))
        # Min index
        iMin = np.min(allcon)
        if iMin!=0:
            raise Exception('Connectivity table for object `{}` needs to have 0 as a minimum  node index'.format(self.name))
        # Max number of nodes
        iMax = np.max(allcon)
        nNodes = self.nNodes
        if iMax!=nNodes-1:
            raise Exception('Connectivity table for objet `{}` needs to have {} as a maximum, corresponding to the maximum number of nodes'.format(self.name, nNodes-1))
        # Check that all nodes indices are present
        IC = np.unique(allcon)
        IA = np.arange(0,nNodes)
        ID = np.setdiff1d(IA,IC)
        if len(ID)>0:
            raise Exception('Connectivity table for object `{}` is missing the following indices : {}.'.format(self.name, ID))
        # --- Add
        self.Connectivity = connectivity.tolist()

    def setElemProps(self, props):
        """ 
        props: 
              list of dictionary, for each element
            OR
              dictionary to be applied for all elements
        """
        if props is None:
            self.ElemProps=None
            return
        # --- Sanity
        if self.Connectivity is None:
            raise Exception('Set Connectivity before setting ElemProps for object {}'.format(self.name))
        if type(props) is dict:
            props=[props]*self.nElem # We repeat the property
        else:
            if len(props) != self.nElem:
                raise Exception('Cannot add ElemProp for object `{}`, its size ({}) does not match connectivity table size.'.format(objname, len(props), self.nElem))
        # Add
        self.ElemProps = props

    def addMode(self, displ, name, freq=1, group='default', **kwargs):
        self.Modes[name] = Mode(displ, name, freq, group=group, **kwargs) 

    def addTimeSeries(self, time, mat4=None, displ=None, rot=None, name=None, group='default'):
        """ add Tiem Series to a connected Object
        See class `TimeSeries` for description of inputs """
        if name is None:
            name='TS '+str(len(self.TS))
        TS = TimeSeries(time, displ=displ, rot=rot, mat4=mat4, name=name, group=group)
        self.TimeSeries[name]=TS

    def __repr__(self):
        s=''
        s='<{} {}> with attributes:\n'.format(type(self).__name__, self.name)
        s+='- Nodes, Connectivity, ElemProps, Modes, TimeSeries\n'.format(self.nNodes, self.nElem)
        s+='*nNodes:{} *nElem:{} *nModes:{} *nTS:{}\n'.format(self.nNodes, self.nElem, self.nModes, self.nTS)
        return s


# --------------------------------------------------------------------------------}
# --- Graph
# --------------------------------------------------------------------------------{
class GraphModel(object):
    def __init__(self, Elements=None, Nodes=None, NodePropertySets=None, ElemPropertySets=None, MiscPropertySets=None): # NOTE: do not initialize with [] or dict()!!!
        self.Elements         = Elements if Elements is not None else []
        self.Nodes            = Nodes    if Nodes    is not None else []
        self.NodePropertySets = NodePropertySets if NodePropertySets is not None else dict()
        self.ElemPropertySets = ElemPropertySets if ElemPropertySets is not None else dict()
        self.MiscPropertySets = MiscPropertySets if MiscPropertySets is not None else dict()
        # Optional if division happens 
        self.Members = []
        # Dynamics
        self.Modes   = []
        self.TimeSeries = []
        # Optimization variables
        self._nodeIDs2Elements   = {} # dictionary with key NodeID and value list of ElementID
        self._nodeIDs2Elements   = {} # dictionary with key NodeID and value list of elements
        self._elementIDs2NodeIDs = {} # dictionary with key ElemID and value list of nodes IDs
        self._connectivity =[]# 

    # --- Main setters
    def addNode(self,node):
        self.Nodes.append(node)

    def addElement(self,elem):
        # Giving nodes to element if these were not provided
        elem.nodes=[self.getNode(i) for i in elem.nodeIDs]
        # Giving props to element if these were not provided
        if elem.propIDs is not None:
            elem.nodeProps=[self.getNodeProperty(elem.propset, i) for i in elem.propIDs]
        self.Elements.append(elem)

    # --- Getters
    def getNode(self, nodeID):
        for n in self.Nodes:
            if n.ID==nodeID:
                return n
        raise KeyError('NodeID {} not found in Nodes'.format(nodeID))

    def getElement(self, elemID):
        for e in self.Elements:
            if e.ID==elemID:
                return e
        raise KeyError('ElemID {} not found in Elements'.format(elemID))

    def getMember(self, membID):
        for m in self.Members:
            if m.ID==membID:
                return m
        raise KeyError('MemberID {} not found in Members'.format(membID))

    def getMemberElements(self, membID):
        m = self.getMember(membID)
        return m.getElements(graph=self)

    def getMemberNodes(self, membID):
        m = self.getMember(membID)
        return m.getNodes(graph=self)

    def getNodeProperty(self, setname, propID):
        for p in self.NodePropertySets[setname]:
            if p.ID==propID:
                return p
        raise KeyError('PropID {} not found for Node propset {}'.format(propID,setname))

    def getElementProperty(self, setname, propID):
        for p in self.ElemPropertySets[setname]:
            if p.ID==propID:
                return p
        raise KeyError('PropID {} not found for Element propset {}'.format(propID,setname))

    def getMiscProperty(self, setname, propID):
        for p in self.MiscPropertySets[setname]:
            if p.ID==propID:
                return p
        raise KeyError('PropID {} not found for Misc propset {}'.format(propID,setname))

    # --- Useful connectivity 
    def node2Elements(self, node):
        return [e for e in self.Elements if node.ID in e.nodeIDs]

    def elements2nodes(self, elements):
        """ Return unique list of nodes involved in a list of elements"""
        nodeIDs=[]
        for e in elements:
            for nID in e.nodeIDs:
                if nID not in nodeIDs:
                    nodeIDs.append(nID)
        nodes = [n for n in self.Nodes if n.ID in nodeIDs]
        return nodes


    @property
    def nodeIDs2ElementIDs(self):
        """ Return list of elements IDs connected to each node"""
        if len(self._nodeIDs2ElementIDs) == 0:
            # Compute list of connected elements for each node
            self._nodeIDs2ElementIDs=dict()
            for i,n in enumerate(self.Nodes):
                self._nodeIDs2ElementIDs[n.ID] = [e.ID for e in self.Elements if n.ID in e.nodeIDs]
        return self._nodeIDs2ElementIDs

    @property
    def nodeIDs2Elements(self):
        """ Return list of elements connected to each node"""
        if len(self._nodeIDs2Elements) == 0:
            # Compute list of connected elements for each node
            self._nodeIDs2Elements
            for i,n in enumerate(self.Nodes):
                self._nodeIDs2Elements[n.ID] = [e for e in self.Elements if n.ID in e.nodeIDs]
        return self._nodeIDs2Elements

    @property
    def elementIDs2NodeIDs(self):
        """ returns """
        if len(self._elementIDs2NodeIDs) ==0:
            self._elementIDs2NodeIDs =dict()
            for e in self.Elements:
                self._elementIDs2NodeIDs[e.ID] = [n.ID for n in e.nodes] 
        return self._elementIDs2NodeIDs

    @property
    def connectivity(self):
        """ returns connectivity, assuming points are indexed starting at 0 
        NOTE: this is basically element2Nodes but reindexed
        """
        if len(self._connectivity) ==0:
            self._connectivity = [[self.Nodes.index(n)  for n in e.nodes] for e in self.Elements]
        return self._connectivity

    def areElementsConnected(self,e1,e2):
        common = set(e1.nodeIDs).intersection(set(e2.nodeIDs))
        return len(common)>0

    # --- Handling of (element/material) Properties
    def addElementPropertySet(self, setname):
        self.ElemPropertySets[setname]= []

    def addNodePropertySet(self, setname):
        self.NodePropertySets[setname]= []

    def addMiscPropertySet(self, setname):
        self.MiscPropertySets[setname]= []

    def addNodeProperty(self, setname, prop):
        if not isinstance(prop, NodeProperty):
            print(type(prop))
            raise Exception('Property needs to inherit from NodeProperty')
        self.PropertySets[setname].append(prop)

    def addNodeProperty(self, setname, prop):
        if not isinstance(prop, NodeProperty):
            print(type(prop))
            raise Exception('Property needs to inherit from NodeProperty')
        self.NodePropertySets[setname].append(prop)

    def addElementProperty(self, setname, prop):
        if not isinstance(prop, ElemProperty):
            print(type(prop))
            raise Exception('Property needs to inherit from ElementProperty')
        self.ElemPropertySets[setname].append(prop)

    def addMiscProperty(self, setname, prop):
        if not isinstance(prop, ElemProperty):
            print(type(prop))
            raise Exception('Property needs to inherit from Property')
        self.MiscPropertySets[setname].append(prop)

    # --- Data and node and element prop setters
    def setElementNodalProp(self, elem, propset, propIDs):
        """ 
        Set Nodal Properties to each node of an element
        """
        for node, pID in zip(elem.nodes, propIDs):
            node.setData(self.getNodeProperty(propset, pID).data)

    def setNodeNodalProp(self, node, propset, propID):
        """ 
        Set Nodal Properties to a node
        """
        node.setData(self.getNodeProperty(propset, propID).data)

    def setNodalData(self, nodeID, **data_dict):
        self.getNode(nodeID).setData(data_dict)

    def __repr__(self):
        s='<{} object> with keys:\n'.format(type(self).__name__)
        s+='- Nodes ({}):\n'.format(len(self.Nodes))
        s+='\n'.join(str(n) for n in self.Nodes)
        s+='\n- Elements ({}):\n'.format(len(self.Elements))
        s+='\n'.join(str(n) for n in self.Elements)
        s+='\n- Members ({}):\n'.format(len(self.Members))
        s+='\n'.join(str(n) for n in self.Members)
        s+='\n- NodePropertySets ({}):'.format(len(self.NodePropertySets))
        for k,v in self.NodePropertySets.items():
            s+='\n> {} ({}):\n'.format(k, len(v))
            s+='\n'.join(str(p) for p in v)
        s+='\n- ElementPropertySets ({}):'.format(len(self.ElemPropertySets))
        for k,v in self.ElemPropertySets.items():
            s+='\n> {} ({}):\n'.format(k, len(v))
            s+='\n'.join(str(p) for p in v)
        s+='\n- MiscPropertySets ({}):'.format(len(self.MiscPropertySets))
        for k,v in self.MiscPropertySets.items():
            s+='\n> {} ({}):\n'.format(k, len(v))
            s+='\n'.join(str(p) for p in v)
        s+='\n- Modes ({}):\n'.format(len(self.Modes))
        s+='\n'.join(str(m) for m in self.Modes)
        s+='\n- TimeSeries ({}):'.format(len(self.TimeSeries))
        for m in self.TimeSeries:
            s+='\n> {}\n'.format({k:v for k,v in m.items() if not isinstance(v,np.ndarray)})
        return s

    # --------------------------------------------------------------------------------}
    # --- Geometrical properties 
    # --------------------------------------------------------------------------------{
    @property
    def extent(self):
        xmax=np.max([node.x for node in self.Nodes])
        ymax=np.max([node.y for node in self.Nodes])
        zmax=np.max([node.z for node in self.Nodes])
        xmin=np.min([node.x for node in self.Nodes])
        ymin=np.min([node.y for node in self.Nodes])
        zmin=np.min([node.z for node in self.Nodes])
        return [xmin,ymin,zmin],[xmax,ymax,zmax],[xmax-xmin,ymax-ymin,zmax-zmin]

    @property
    def maxDimension(self):
        _,_,D=self.extent
        return np.max(D)

    @property
    def points(self):
        nNodes = len(self.Nodes)
        Points = np.zeros((nNodes,3))
        for i,n in enumerate(self.Nodes):
            Points[i,:]=(n.x, n.y, n.z)
        return Points

    def toLines(self, output='coord'):
        if output=='coord':
            lines = np.zeros((len(self.Elements), 2, 3)) # 
            for ie, e in enumerate(self.Elements):
                n1=e.nodes[0]
                n2=e.nodes[-1]
                lines[ie, 0, : ] = (n1.x, n1.y, n1.z)
                lines[ie, 1, : ] = (n2.x, n2.y, n2.z)
        elif output=='lines3d':
            import mpl_toolkits.mplot3d as plt3d
            lines=[]
            for ie, e in enumerate(self.Elements):
                n1=e.nodes[0]
                n2=e.nodes[-1]
                line = plt3d.art3d.Line3D((n1.x,n2.x), (n1.y,n2.y), (n1.z,n2.z))
                lines.append(line)
        else:
            raise NotImplementedError()

        return lines

    # --------------------------------------------------------------------------------}
    # --- Change of connectivity
    # --------------------------------------------------------------------------------{
    def connecticityHasChanged(self):
        self._nodeIDs2ElementIDs = dict()
        self._nodeIDs2Elements   = dict()
        self._elementIDs2NodeIDs = dict()
        self._connectivity=[]

    def updateConnectivity(self):
        for e in self.Elements:
            e.nodes=[self.getNode(i) for i in e.nodeIDs]

        for e in self.Elements:
            if e.propIDs is not None:
                e.nodeProps = [self.getNodeProperty(e.propset, ID) for ID in e.propIDs]
        # Potentially call nodeIDs2ElementIDs etc

    def reindexNodes(self, offset=0):
        """ Change node IDs so that the increase linearly"""
        for i,n in enumerate(self.Nodes):
            n.ID = i+offset
        self.nodeIDsHaveChanged() #$ trigger for element.nodeIDs

    def nodeIDsHaveChanged(self):
        """ 
        If User changes node.ID for the nodes, change the elements to reflect that
        """
        for e in self.Elements:
            e.nodeIDs=[n.ID for n in e.nodes]

    def sortNodesBy(self,key):
        """ Sort nodes, will affect the connectivity, but node IDs remain the same"""

        # TODO, that's quite doable
        if len(self.Modes)>0:
            raise Exception('Cannot sort nodes when mode data is present')
        if len(self.TimeSeries)>0:
            raise Exception('Cannot sort nodes when timeseries are present')

        nNodes = len(self.Nodes)
        if key=='x':
            values=[n.x for n in self.Nodes]
        elif key=='y':
            values=[n.y for n in self.Nodes]
        elif key=='z':
            values=[n.z for n in self.Nodes]
        elif key=='ID':
            values=[n.ID for n in self.Nodes]
        else:
            values=[n[key] for n in self.Nodes]
        I= np.argsort(values)
        self.Nodes=[self.Nodes[i] for i in I]

        # Trigger, remove precomputed values related to connectivity:
        self.connecticityHasChanged()

        return self


    def _divideElement(self, elemID, nPerElement, maxElemId, keysNotToCopy=None):
        """ divide a given element by nPerElement (add nodes and elements to graph) """ 
        if len(self.Modes)>0:
            raise Exception('Cannot divide graph when mode data is present')
        if len(self.TimeSeries)>0:
            raise Exception('Cannot divide graph when motion data is present')
        keysNotToCopy = [] if keysNotToCopy is None else keysNotToCopy

        maxNodeId=np.max([n.ID for n in self.Nodes])
        e = self.getElement(elemID)
        newElems = []
        if len(e.nodes)==2:
            n1=e.nodes[0]
            n2=e.nodes[1]
            subNodes=[n1]
            for iSub in range(1,nPerElement):
                maxNodeId += 1
                #data_dict  = n1.data.copy()
                data_dict  = dict()
                fact       = float(iSub)/nPerElement
                # Interpolating position
                x          = n1.x*(1-fact)+n2.x*fact
                y          = n1.y*(1-fact)+n2.y*fact
                z          = n1.z*(1-fact)+n2.z*fact
                # Interpolating data (only if floats)
                for k,v in n1.data.items():
                    if k not in keysNotToCopy:
                        try:
                            data_dict[k] = n1.data[k]*(1-fact) + n2.data[k]*fact
                        except:
                            data_dict[k] = n1.data[k]
                ni = Node(maxNodeId, x, y, z, **data_dict)
                subNodes.append(ni)
                self.addNode(ni)
            subNodes+=[n2]
            e.nodes  =subNodes[0:2]
            e.nodeIDs=[e.ID for e in e.nodes]
            for i in range(1,nPerElement):
                maxElemId+=1
                elem_dict = e.data.copy()
                propset = None
                propIDs = None
                # Creating extra properties if necessary
                if e.propIDs is not None:
                    if all(e.propIDs==e.propIDs[0]):
                        # No need to create a new property
                        propIDs=e.propIDs
                        propset=e.propset
                    else:
                        raise NotImplementedError('Division of element with different properties on both ends. TODO add new property.')
                elem= Element(maxElemId, [subNodes[i].ID, subNodes[i+1].ID], propset=propset, propIDs=propIDs, **elem_dict )
                newElems.append(elem)
        return newElems


    def divideElements(self, nPerElement, excludeDataKey='', excludeDataList=None, method='append', keysNotToCopy=None, verbose=False):
        """ divide all elements by nPerElement (add nodes and elements to graph)

        - excludeDataKey: is provided, will exclude elements such that e.data[key] in `excludeDataList`

        - method: append or insert

        - keysNotToCopy: when duplicating node and element data, make sure not to duplicate data with these keys
                         For instance if a node that has a boundary condition, it should not be passed to the 
                         node that is created when dividing an element.

        Example: 
           to avoid dividing elements of `Type` 'Cable' or `Rigid`, call as follows:
             self.divideElements(3, excludeDataKey='Type', excludeDataList=['Cable','Rigid'] )

        """ 
        keysNotToCopy   = [] if keysNotToCopy is None else keysNotToCopy
        excludeDataList = [] if excludeDataList is None else excludeDataList


        maxNodeId=np.max([n.ID for n in self.Nodes])
        maxElemId=np.max([e.ID for e in self.Elements])

        if nPerElement<=0:
            raise Exception('nPerElement should be more than 0')

        newElements=[]
        self.Members=[] 
        for ie in np.arange(len(self.Elements)): # cannot enumerate since length increases
            E = self.Elements[ie]
            # Store member as the element might get changed
            memberElemIDs=[E.ID]
            memberNodeIDs=E.nodeIDs
            elemID = E.ID
            if method=='insert':
                newElements+=[self.getElement(elemID)] # newElements contains
            if (len(excludeDataKey)>0 and E.data[excludeDataKey] not in excludeDataList) or len(excludeDataKey)==0:
                elems = self._divideElement(elemID, nPerElement, maxElemId, keysNotToCopy)
                maxElemId+=len(elems)
                newElements+=elems
                memberElemIDs+= [e.ID for e in elems]
            else:
                if verbose:
                    print('Not dividing element with ID {}, based on key `{}` with value `{}`'.format(elemID, excludeDataKey, E.data[excludeDataKey]))
            # We create a member
            m = Member(ID=elemID, elemIDs=memberElemIDs)
            self.Members.append(m)


        # Adding elements at the end
        if method=='append':
            pass
        elif method=='insert':
            self.Elements=[] # We clear all elements
        else:
            raise NotImplementedError('Element Insertions')

        for e in newElements:
            self.addElement(e)

        # Trigger, remove precomputed values related to connectivity:
        self.connecticityHasChanged()

        return self
                    
    # --------------------------------------------------------------------------------}
    # --- Dynamics
    # --------------------------------------------------------------------------------{
    def addMode(self, displ, name=None, freq=1, group='default'):
        """ See class `Mode` for description of inputs """
        if name is None:
            name='Mode '+str(len(self.Modes))
        mode = Mode(displ=displ, name=name, freq=freq, group=group)
        self.Modes.append(mode)

    def addTimeSeries(self, time, mat4=None, displ=None, rot=None, name=None, group='default'):
        """ See class `TimeSeries` for description of inputs """
        if name is None:
            name='TS '+str(len(self.TS))
        TS = TimeSeries(time, displ=displ, rot=rot, mat4=mat4, name=name, group=group)
        self.TimeSeries.append(TS)


    # --------------------------------------------------------------------------------}
    # --- Ouputs / converters
    # --------------------------------------------------------------------------------{
    def nodalDataFrame(self, sortBy=None):
        """ return a DataFrame of all the nodal data """
        data=dict()
        nNodes=len(self.Nodes)
        for i,n in enumerate(self.Nodes):
            if i==0:
                data['ID'] = np.zeros(nNodes).astype(int)
                data['x']  = np.zeros(nNodes)
                data['y']  = np.zeros(nNodes)
                data['z']  = np.zeros(nNodes)

            data['ID'][i] = n.ID
            data['x'][i]  = n.x
            data['y'][i]  = n.y
            data['z'][i]  = n.z
            for k,v in n.data.items():
                if k not in data:
                    data[k] = np.zeros(nNodes)
                try:
                    data[k][i]=v
                except:
                    pass
        df = pd.DataFrame(data)
        # Sorting 
        if sortBy is not None:
            df.sort_values([sortBy],inplace=True,ascending=True)
            df.reset_index(drop=True,inplace=True) 
        return df


    def toJSON(self,outfile=None):
        # TODO use json3d/ Assembly Of Objects
        d=dict();
        Points=self.points
        d['Connectivity'] = self.connectivity
        d['Nodes']        = Points.tolist()
        
        d['ElemProps']=list()
        for iElem,elem in enumerate(self.Elements):
            Shape = elem.data['shape'] if 'shape' in elem.data.keys() else 'cylinder'
            Type  = elem.data['TypeID'] if 'TypeID' in elem.data.keys() else 1
            try:
                Diam  = elem.D
            except:
                Diam  = elem.data['D'] if 'D' in elem.data.keys() else 1
            if Shape=='cylinder':
                d['ElemProps'].append({'shape':'cylinder','type':Type, 'Diam':Diam})
            else:
                raise NotImplementedError()


        allGroups= np.unique([m['group'] for m in self.Modes]) 
        d['Modes']=dict()
        for g in allGroups:
            d['Modes'][g] = [{ 
                'name': mode['name'],
                'omega':mode['freq']*2*np.pi, #in [rad/s]
                'Displ':mode['displ'].tolist()
                }  for iMode,mode in enumerate(self.Modes) if mode['group']==g]

        allGroups= np.unique([ts['group'] for ts in self.TimeSeries]) 
        d['TimeSeries']=dict()
        for g in allGroups:
            d['TimeSeries'][g] = [{ 
                'name':       TS['name'],
                'timeInfo':   TS.timeInfo,
                'absolute':   TS['absolute'],
                'perElement': TS['perElement'],
                'mat4':     TS.mat4(flat=True),
                }  for iTS,TS in enumerate(self.TimeSeries) if TS['group']==g]

        d['groundLevel']=np.min(Points[:,2]) # TODO

        if outfile is not None:
            import json
            from io import open
            jsonFile=outfile
            with open(jsonFile, 'w', encoding='utf-8') as f:
                #f.write(to_json(d))
                try:
                    #f.write(unicode(json.dumps(d, ensure_ascii=False))) #, indent=2)
                    #f.write(json.dumps(d, ensure_ascii=False)) #, indent=2)
                    f.write(json.dumps(d, ensure_ascii=False))
                except:
                    print('>>> FAILED')
                    json.dump(d, f, indent=0) 
        return d

# 



INDENT = 3
SPACE = " "
NEWLINE = "\n"
# Changed basestring to str, and dict uses items() instead of iteritems().

def to_json(o, level=0):
  ret = ""
  if isinstance(o, dict):
    if level==0:
        ret += "{" + NEWLINE
        comma = ""
        for k, v in o.items():
          ret += comma
          comma = ",\n"
          ret += SPACE * INDENT * (level + 1)
          ret += '"' + str(k) + '":' + SPACE
          ret += to_json(v, level + 1)
        ret += NEWLINE + SPACE * INDENT * level + "}"
    else:
        ret += "{" 
        comma = ""
        for k, v in o.items():
          ret += comma
          comma = ",\n"
          ret += SPACE
          ret += '"' + str(k) + '":' + SPACE
          ret += to_json(v, level + 1)
        ret += "}"

  elif isinstance(o, str):
    ret += '"' + o + '"'
  elif isinstance(o, list):
    ret += "[" + ",".join([to_json(e, level + 1) for e in o]) + "]"
  # Tuples are interpreted as lists
  elif isinstance(o, tuple):
    ret += "[" + ",".join(to_json(e, level + 1) for e in o) + "]"
  elif isinstance(o, bool):
    ret += "true" if o else "false"
  elif isinstance(o, int):
    ret += str(o)
  elif isinstance(o, float):
    ret += '%.7g' % o
  elif isinstance(o, numpy.ndarray) and numpy.issubdtype(o.dtype, numpy.integer):
    ret += "[" + ','.join(map(str, o.flatten().tolist())) + "]"
  elif isinstance(o, numpy.ndarray) and numpy.issubdtype(o.dtype, numpy.inexact):
    ret += "[" + ','.join(map(lambda x: '%.7g' % x, o.flatten().tolist())) + "]"
  elif o is None:
    ret += 'null'
  else:
    raise TypeError("Unknown type '%s' for json serialization" % str(type(o)))
  return ret
