<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis hasScaleBasedVisibilityFlag="0" maxScale="0" version="3.4.15-Madeira" styleCategories="AllStyleCategories" labelsEnabled="0" simplifyAlgorithm="0" simplifyMaxScale="1" simplifyDrawingTol="1" minScale="1e+08" simplifyDrawingHints="1" simplifyLocal="1" readOnly="0">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" enableorderby="0" symbollevels="0" type="singleSymbol">
    <symbols>
      <symbol alpha="1" name="0" clip_to_extent="1" type="line" force_rhr="0">
        <layer class="SimpleLine" pass="0" locked="0" enabled="1">
          <prop k="capstyle" v="square"/>
          <prop k="customdash" v="5;2"/>
          <prop k="customdash_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="customdash_unit" v="MM"/>
          <prop k="draw_inside_polygon" v="0"/>
          <prop k="joinstyle" v="bevel"/>
          <prop k="line_color" v="164,113,88,255"/>
          <prop k="line_style" v="solid"/>
          <prop k="line_width" v="0.26"/>
          <prop k="line_width_unit" v="MM"/>
          <prop k="offset" v="0"/>
          <prop k="offset_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <prop k="offset_unit" v="MM"/>
          <prop k="ring_filter" v="0"/>
          <prop k="use_custom_dash" v="0"/>
          <prop k="width_map_unit_scale" v="3x:0,0,0,0,0,0"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property key="dualview/previewExpressions">
      <value>"id"</value>
    </property>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory maxScaleDenominator="1e+08" enabled="0" penColor="#000000" height="15" penWidth="0" backgroundColor="#ffffff" lineSizeScale="3x:0,0,0,0,0,0" diagramOrientation="Up" barWidth="5" sizeType="MM" minScaleDenominator="0" labelPlacementMethod="XHeight" backgroundAlpha="255" scaleDependency="Area" scaleBasedVisibility="0" lineSizeType="MM" minimumSize="0" opacity="1" rotationOffset="270" penAlpha="255" width="15" sizeScale="3x:0,0,0,0,0,0">
      <fontProperties description="Ubuntu,11,-1,5,50,0,0,0,0,0" style=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings placement="2" obstacle="0" dist="0" priority="0" showAll="1" zIndex="0" linePlacementFlags="18">
    <properties>
      <Option type="Map">
        <Option name="name" value="" type="QString"/>
        <Option name="properties"/>
        <Option name="type" value="collection" type="QString"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions removeDuplicateNodes="0" geometryPrecision="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="id">
      <editWidget type="Hidden">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="name">
      <editWidget type="ValueMap">
        <config>
          <Option type="Map">
            <Option name="map" type="List">
              <Option type="Map">
                <Option name="A" value="a" type="QString"/>
              </Option>
              <Option type="Map">
                <Option name="B" value="b" type="QString"/>
              </Option>
              <Option type="Map">
                <Option name="C" value="c" type="QString"/>
              </Option>
            </Option>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="checkbox">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option name="IsMultiline" value="false" type="bool"/>
            <Option name="UseHtml" value="false" type="bool"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="value_map">
      <editWidget type="ValueMap">
        <config>
          <Option type="Map">
            <Option name="map" type="List">
              <Option type="Map">
                <Option name="A" value="a" type="QString"/>
              </Option>
              <Option type="Map">
                <Option name="B" value="b" type="QString"/>
              </Option>
              <Option type="Map">
                <Option name="C" value="c" type="QString"/>
              </Option>
            </Option>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="photo">
      <editWidget type="ExternalResource">
        <config>
          <Option type="Map">
            <Option name="DocumentViewer" value="1" type="int"/>
            <Option name="DocumentViewerHeight" value="0" type="int"/>
            <Option name="DocumentViewerWidth" value="0" type="int"/>
            <Option name="FileWidget" value="true" type="bool"/>
            <Option name="FileWidgetButton" value="true" type="bool"/>
            <Option name="FileWidgetFilter" value="" type="QString"/>
            <Option name="PropertyCollection" type="Map">
              <Option name="name" value="" type="QString"/>
              <Option name="properties"/>
              <Option name="type" value="collection" type="QString"/>
            </Option>
            <Option name="RelativeStorage" value="0" type="int"/>
            <Option name="StorageMode" value="0" type="int"/>
          </Option>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias index="0" field="id" name=""/>
    <alias index="1" field="name" name=""/>
    <alias index="2" field="checkbox" name=""/>
    <alias index="3" field="value_map" name=""/>
    <alias index="4" field="photo" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="id" expression="" applyOnUpdate="0"/>
    <default field="name" expression="" applyOnUpdate="0"/>
    <default field="checkbox" expression="" applyOnUpdate="0"/>
    <default field="value_map" expression="" applyOnUpdate="0"/>
    <default field="photo" expression="" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint field="id" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="name" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="checkbox" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="value_map" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="photo" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" field="id" desc=""/>
    <constraint exp="" field="name" desc=""/>
    <constraint exp="" field="checkbox" desc=""/>
    <constraint exp="" field="value_map" desc=""/>
    <constraint exp="" field="photo" desc=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortOrder="0" sortExpression="">
    <columns>
      <column name="id" width="-1" hidden="0" type="field"/>
      <column name="name" width="-1" hidden="0" type="field"/>
      <column width="-1" hidden="1" type="actions"/>
      <column name="checkbox" width="-1" hidden="0" type="field"/>
      <column name="value_map" width="-1" hidden="0" type="field"/>
      <column name="photo" width="-1" hidden="0" type="field"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
Les formulaires QGIS peuvent avoir une fonction Python qui sera appelée à l'ouverture du formulaire.

Utilisez cette fonction pour ajouter plus de fonctionnalités à vos formulaires.

Entrez le nom de la fonction dans le champ "Fonction d'initialisation Python".
Voici un exemple à suivre:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
    geom = feature.geometry()
    control = dialog.findChild(QWidget, "MyLineEdit")

]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>tablayout</editorlayout>
  <attributeEditorForm>
    <attributeEditorContainer name="tab 1" columnCount="1" groupBox="0" visibilityExpression="" visibilityExpressionEnabled="0" showLabel="1">
      <attributeEditorField index="0" name="id" showLabel="1"/>
      <attributeEditorField index="1" name="name" showLabel="1"/>
      <attributeEditorField index="2" name="checkbox" showLabel="1"/>
      <attributeEditorField index="3" name="value_map" showLabel="1"/>
    </attributeEditorContainer>
    <attributeEditorContainer name="tab2" columnCount="1" groupBox="0" visibilityExpression="" visibilityExpressionEnabled="0" showLabel="1">
      <attributeEditorField index="4" name="photo" showLabel="1"/>
    </attributeEditorContainer>
  </attributeEditorForm>
  <editable>
    <field name="checkbox" editable="1"/>
    <field name="id" editable="1"/>
    <field name="name" editable="1"/>
    <field name="photo" editable="1"/>
    <field name="value_map" editable="1"/>
  </editable>
  <labelOnTop>
    <field name="checkbox" labelOnTop="0"/>
    <field name="id" labelOnTop="0"/>
    <field name="name" labelOnTop="0"/>
    <field name="photo" labelOnTop="0"/>
    <field name="value_map" labelOnTop="0"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>id</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>1</layerGeometryType>
</qgis>
