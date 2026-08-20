import pandas as pd

df_requirements = pd.read_csv('./docs/requirements.csv')
df_requirement_scenario = pd.read_csv('./docs/requirements-scenario-map.csv')
df_defects = pd.read_csv('./docs/defects.csv')

merged = pd.merge(df_defects, df_requirements, left_on='Requirement', right_on='Code')

print(merged)

merged.rename(columns={
    0: 'Index',
    'Issue No.': 'Issue No.',
    'Requirement_x': 'Requirement Code',
    'Scenario': 'Scenario',
    'Defect': 'Defect',
    'Score': 'Impact Score',
    'Work Estimate': 'Work',
    'Code': 'Requirement Code duplicate',
    'Feature': 'Feature',
    'Requirement_y': 'Requirement Name',
    'Description': 'Description',
}, inplace=True)

merged.drop(columns=['Requirement Code duplicate'])
reordered = merged[[
    'Issue No.',
    'Requirement Code',
    'Feature',
    'Requirement Name',
    'Scenario',
    'Defect',
    'Impact Score',
    'Work',
]]
reordered.to_csv('docs/defect-merged.csv')

reorder_unique_features = reordered['Feature'].unique()

print(' ')
print('## Issue Counts:')
for feature in reorder_unique_features:
    df_filtered_on_feature = reordered[reordered['Feature'] == feature]
    df_filtered_by_severity = df_filtered_on_feature[df_filtered_on_feature['Impact Score'] >= 5]
    print(feature, len(df_filtered_on_feature))
    print('   Number of automatic UAT blockers: ', len(df_filtered_by_severity))
    print('   Highest Severity: ', df_filtered_on_feature['Impact Score'].max())
    print('   Lowest Severity: ', df_filtered_on_feature['Impact Score'].min())
    print('   Highest Effort: ', df_filtered_on_feature['Work'].max())
    print('   Lowest Effort: ', df_filtered_on_feature['Work'].min())
    print('   Effort Avg: ', df_filtered_on_feature['Work'].mean())


requirement_unique_features = df_requirements['Feature'].unique()

print(' ')
print('## Requirement Counts:')
for feature in requirement_unique_features:
    df_filtered = df_requirements[df_requirements['Feature'] == feature]
    print(feature, len(df_filtered))

unique_verification_methods = df_requirement_scenario['Verification Method'].unique()

print(' ')
print('## Verification Methods')
print(unique_verification_methods)

for vm in unique_verification_methods:
    df_vm = df_requirement_scenario[df_requirement_scenario['Verification Method'] == vm]
    print('   - ', vm, ': ', len(df_vm))
