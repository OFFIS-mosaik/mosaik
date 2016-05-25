package de.offis.mosaik.api.utils;


import java.util.Map;

import org.json.simple.JSONObject;
import org.json.simple.JSONValue;

import de.offis.mosaik.api.Simulator;

import org.json.simple.JSONArray;

/**
 * Class to encapsulate the creation of MetaOutputs which the
 * {@link de.offis.mosaik.api.Simulator#init(String, Map) init()}
 * API function needs to return. You can add models and methods
 * individually or by parsing a JSON String.
 * @author tLaue
 */

@SuppressWarnings("unchecked")
public class MetaBuilder {

	private JSONObject models;

	private JSONArray extraMethods;
	
	/**
	 * Creates a new meta object, with the "api_version" value already set.
	 */
	public MetaBuilder() {
		this.models = new JSONObject();
		this.extraMethods = new JSONArray();
	}
	
	/**
	 * Add a new model to the meta object.
	 * @param name The name of the model.
	 * @param isPublic Specifies whether the model can be instantiated by
	 * a user.
	 * @param params The models parameters, which are set on creation.
	 * @param attrs The models accessible attributes.
	 */
	public void addModel(String name, boolean isPublic, String[] params, 
			String[] attrs) {
		if (name == null || params == null || attrs == null) {
			throw new RuntimeException("Name, params and attrs "
					+ "can not be null");
		}
		
		JSONArray paramsArray = new JSONArray();
		for (String str : params) {
			paramsArray.add(str);
		}
		
		JSONArray attrsArray = new JSONArray();
		for (String str : attrs) {
			attrsArray.add(str);
		}
		//TODo check unique model name! Fail early
		JSONObject modelsEntry = new JSONObject();
		modelsEntry.put("params", paramsArray);
		modelsEntry.put("attrs", attrsArray);
		modelsEntry.put("public", isPublic);
		models.put(name, modelsEntry);
	}
	
	/**
	 * Add an extra method to the meta object.
	 * @param name The name of the method.
	 */
	public void addExtraMethod(String name) {
		if (name == null) {
			throw new RuntimeException("Name can not be null");
		}
		if (extraMethods.contains(name)) {
			throw new RuntimeException("Extra method \"" + name 
					+ "\" already exists!");
		}

		extraMethods.add(name);
	}
	
	/**
	 * Get the output of this builder in a format your 
	 * {@link de.offis.mosaik.api.Simulator#init(String, Map) init()}
	 * implementation can return it directly.
	 * @return The collected data.
	 */
	public Map<String, Object> getOutput(){
		JSONObject result = new JSONObject();
		result.put("api_version", Simulator.API_VERSION);
		result.put("models", models);
		if (!extraMethods.isEmpty()) {
			result.put("extra_methods", extraMethods);
		}
		return result;
	}
	
	/**
	 * Read a JSON String and convert it to a format your 
	 * {@link de.offis.mosaik.api.Simulator#init(String, Map) init()}
	 * implementation can return it directly.
	 * @param json The JSON String.
	 */
	public Map<String, Object> parseJSONstring(String json) {
		return (JSONObject) JSONValue.parse(json);
	}
}
