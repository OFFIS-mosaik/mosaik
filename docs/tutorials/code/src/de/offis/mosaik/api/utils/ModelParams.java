package de.offis.mosaik.api.utils;

import java.util.Collection;
import java.util.Map;
import java.util.Set;

/**
 * Contains a set of model parameter names and their associated values, which
 * should be set on the newly created entities within your 
 * {@link de.offis.mosaik.api.Simulator#create(int, String, Map) create()} 
 * implementation.
 * @author tLaue
 *
 */
public class ModelParams {

	private Map<String, Object> params;
	
	@SuppressWarnings("unused")
	private ModelParams(){};
	
	/**
	 * Create a new ModelParams instance.
	 * @param simParams The parameter mapping sent by mosaik.
	 */
	public ModelParams(Map<String, Object> modelParams) {
		this.params = modelParams;
	}

	/**
	 * Returns true if the parameter name specified is contained in this 
	 * object.
	 * @param paramName The parameter name whose presence is to be tested.
	 * @return True, if paramName could be found.
	 */
	public boolean containsKey(String paramName) {
		return params.containsKey(paramName);
	}

	/**
	 * Returns true if this object holds the specified value at least once.
	 * @param value Value whose presence is to be tested.
	 * @return true if this map object hold the specified value at least once.
	 */
	public boolean containsValue(Object value) {
		return params.containsValue(value);
	}

	/**
	 * Returns a Set view of the parameter-value pairs contained in this 
	 * object.
	 * @return A set view of the mappings contained in this map
	 */
	public Set<java.util.Map.Entry<String, Object>> entrySet() {
		return params.entrySet();
	}

	/**
	 * Returns the value to which the specified parameter name is mapped,
	 * or null,
	 * if the key is not present among the parameters in this object.
	 * @param paramName The name of the parameter whose associated value you
	 * want to retrieve.
	 * @return The value, or null.
	 */
	public Object get(String paramName) {
		return params.get(paramName);
	}
	
	/**
	 * Check whether this object holds no parameters.
	 * @return True, if this object has an empty set of parameters.
	 */
	public boolean isEmpty() {
		return params.isEmpty();
	}

	/**
	 * Returns a Set view of the parameter names contained in this object.
	 * @return A Set view of the parameter names contained in this object.
	 */
	public Set<String> keySet() {
		return params.keySet();
	}

	/**
	 * Returns the number of parameter-value mappings in this object.
	 * @return The number of parameter-value mappings in this object.
	 */
	public int size() {
		return params.size();
	}

	/**
	 * Returns a Collection view of the values contained in this object.
	 * @return A Collection view of the values contained in this object.
	 */
	public Collection<Object> values() {
		return params.values();
	}

	/**
	 * Get the raw data sent by mosaik.
	 * @return the data.
	 */
	public Map<String, Object> getRawData() {
		return this.params;
	}
}
