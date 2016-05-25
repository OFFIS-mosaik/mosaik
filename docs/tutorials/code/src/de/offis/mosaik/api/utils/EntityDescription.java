package de.offis.mosaik.api.utils;

import java.util.HashMap;
import java.util.LinkedList;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;


/**
 * Represents an entity and holds all information concerning it. Can
 * be created by using an 
 * {@link de.offis.mosaik.api.utils.EntityDescriptionBuilder
 * EntityDescriptionBuilder}.
 * @author tLaue
 */
@SuppressWarnings("unchecked")
public class EntityDescription {

	private String entityID;
	private String entityType;
	private String[] entityRelations;
//	boolean entityWasOutPut = false;

	private LinkedList<EntityDescription> entityChildren;
	private HashMap<String, Integer> modelCounts = new HashMap<>();
	
	@SuppressWarnings("unused")
	private EntityDescription(){};
	
	/**
	 * Creates a new EntityDescription.
	 * @param eid The unique ID of this entity.
	 * @param type The model type of this entity.
	 * @param rel A list of the IDs of related entities (optional).
	 */
	EntityDescription(String eid, String type, String[] rel) {
		this.entityID = eid;
		if (type == null) {
			throw new RuntimeException("type can not be null.");
		}
		this.entityType = type;
		if (rel == null) {
			this.entityRelations = new String[0];
		} else {
			this.entityRelations = rel;
		}
		this.entityChildren = new LinkedList<EntityDescription>();
	}
	
	/**
	 * Add a child to this entity's "children" entry.
	 * Will throw an exception if the entity ID already exists, or if
	 * type or eid is null.
	 * @param eid The unique ID of the entity.
	 * @param type The model type of this entity.
	 * @param rel A list of the IDs of related entities (optional).
	 * @return The newly created child entity as a
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription}
	 * instance (can be used for appending children entities to it).<br>
	 * <em>Warning:</em> Returned EntityDescription Objects are no deep 
	 * copies, thus all changes to any of them will affect the collected 
	 * data of this builder instance as well as all its future outputs.
	 */
	public EntityDescription addChild(String eid, String type, String[] rel) {
		if (type == null || eid == null) {
			throw new RuntimeException("type can not be null.");
		}

		Integer count = modelCounts.get(type);
		if (count == null) {
			count = new Integer(0);
			modelCounts.put(type, count);
		}
		int countInt = count.intValue();
		
		countInt++;
		modelCounts.put(type, new Integer(countInt));
		
		EntityDescription ent2 = this.getChildByEid(eid);
		if (ent2 != null) {
			throw new RuntimeException("Eid " + eid + " is not unique! Type: "
					+ ent2.entityType + ", EID: "+ ent2.entityID);
		}
		
		EntityDescription entity = new EntityDescription(eid, type, rel);
		this.entityChildren.add(entity);
		return entity;
	}
	
	/**
	 * Add a child to this entity's "children" entry. This function will 
	 * automatically generate an EID for the child, following the scheme<br>
	 * {@code [parents eid]+_+[child entity type]+_+[0 based index of
	 * children of the same type]}<br>
	 * Will throw an exception if the entities ID already exists,
	 * or if type is null.
	 * @param type The model type of this entity.
	 * @param rel A list of the IDs of related entities (optional).
	 * @return The newly created child entity as a
	 * {@link de.offis.mosaik.api.utils.EntityDescription EntityDescription}
	 * instance (can be used for appending children entities to it)<br>
	 * <em>Warning:</em> Returned EntityDescription Objects are no deep
	 * copies, thus all changes to any of them will affect the collected
	 * data of this builder instance as well as all its future outputs.
	 */
	public EntityDescription addChild(String type, String[] rel) {
		if (type == null) {
			throw new RuntimeException("type can not be null.");
		}

		Integer count = modelCounts.get(type);
		if (count == null) {
			count = new Integer(0);
			modelCounts.put(type, count);
		}
		int countInt = count.intValue();
		
		String autoEid = this.entityID + "_" + type + "_" + countInt;
		
		countInt++;
		modelCounts.put(type, new Integer(countInt));
		
		EntityDescription ent2 = this.getChildByEid(autoEid);
		if (ent2 != null) {
			throw new RuntimeException("Eid " + autoEid + " is not unique! "
					+ "Type: " + ent2.entityType + ", EID: "+ ent2.entityID);
		}
		
		EntityDescription entity = new EntityDescription(autoEid, type, rel);
		this.entityChildren.add(entity);
		return entity;
	}
	
	/**
	 * Get the ID of this entity.
	 * @return The ID of this entity.
	 */
	public String getEID() {
		return entityID;
	}

	/**
	 * Get the type of this entity.
	 * @return The type of this entity.
	 */
	public String getType() {
		return entityType;
	}

	/**
	 * 
	 * @return
	 */
	public String[] getRelations() {
		return entityRelations.clone();
	}

	/**
	 * 
	 * @return
	 */
	public LinkedList<EntityDescription> getChildren() {
		return (LinkedList<EntityDescription>) this.entityChildren.clone();
	}

	/**
	 * Convert this entity (including its children, recursively)
	 * into a JSON object.
	 * @return The representation of this entity as JOSN object.
	 */
	JSONObject toJSONObject() {
		JSONArray relArray = new JSONArray();
        for (String str : this.entityRelations) {
        	relArray.add(str);
        }
		JSONObject entity = new JSONObject();
        entity.put("eid", entityID);
        entity.put("type", entityType);
        entity.put("rel", relArray);
        if (this.entityChildren != null && !this.entityChildren.isEmpty()) {
	        JSONArray childrenArray = new JSONArray();
	        for (EntityDescription e : this.entityChildren) {
	        	childrenArray.add(e.toJSONObject());
	        }
	        entity.put("children", childrenArray);
        }
        
		return entity;
	}

	/**
	 * Find the child of this entity that bears the specified ID,
	 * if it exists.
	 * @param eid The ID in question.
	 * @return The child as EntityDescription, or null.
	 */
	EntityDescription getChildByEid(String eid) {
		EntityDescription result = null;
		for (EntityDescription ent : this.entityChildren) {
			if (ent.getEID().equals(eid)) {
				result = ent;
				break;
			} else if (ent.entityChildren != null) {
				result = ent.getChildByEid(eid);
			}
			if (result != null) {
				break;
			}
		}
		return result;
	}
}
